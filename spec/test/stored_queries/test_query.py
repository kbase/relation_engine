"""
This script can be run from `make`
Essentially it was created to run stored queries against the ncbi_taxon collection
and collect data and stats.
"""

import os
import unittest

# Skip entire module if env var not set
# to avoid non-Docker-container imports or otherwise
# specific/costly operations in script
if not os.environ.get("DO_QUERY_TESTING"):
    raise unittest.SkipTest(
        "Env var DO_QUERY_TESTING not set. Skipping query testing module"
    )

import traceback as tb  # noqa E402
import sys  # noqa E402
import json  # noqa E402
import datetime  # noqa E402
import time  # noqa E402
import random  # noqa E402
import textwrap  # noqa E402
import warnings  # noqa E402
import pytest  # noqa E402
from typing import Tuple, List  # noqa E402
from requests.exceptions import ReadTimeout  # noqa E402

from arango import ArangoClient  # noqa E402
import numpy as np  # noqa E402
import pandas as pd  # noqa E402
import seaborn as sns  # noqa E402
import matplotlib.pyplot as plt  # noqa E402

from relation_engine_server.utils import json_validation  # noqa E402

warnings.filterwarnings("ignore")

# Directories and files
ROOT_DIR = os.getcwd()
CURR_DIR = os.path.join(ROOT_DIR, "spec/test/stored_queries")
CONFIG_FP = os.path.join(ROOT_DIR, "arango_live_server_config.json")
TEST_DATA_DIR = os.path.join(CURR_DIR, "../data")
TMP_OUT_DIR = os.path.join(ROOT_DIR, "tmp")
SCINAMES_LATEST_FP = os.path.join(TMP_OUT_DIR, "ncbi_scinames_latest.json")
SAMPLINGS_FP = os.path.join(TMP_OUT_DIR, "samplings.json")
STORED_QUERY_FP = os.path.join(
    ROOT_DIR, "spec/stored_queries/taxonomy/taxonomy_search_species_strain.yaml"
)
STORED_QUERY_NO_SORT_FP = os.path.join(
    ROOT_DIR, "spec/stored_queries/taxonomy/taxonomy_search_species_strain_no_sort.yaml"
)
STORED_QUERY_OLD_FP = os.path.join(
    ROOT_DIR, "spec/stored_queries/taxonomy/taxonomy_search_species.yaml"
)

if not os.path.exists(TMP_OUT_DIR):
    os.mkdir(TMP_OUT_DIR)

# Read config
try:
    with open(CONFIG_FP) as fh:
        CONFIG = json.load(fh)
    CLIENT = ArangoClient(hosts=CONFIG["host"])
    DB = CLIENT.db("ci", username=CONFIG["username"], password=CONFIG["password"])
except Exception:
    help_msg = """
Please set host URL, username, and password in arango_live_server_config.json, e.g.,
{
    "username": "doe_j",
    "password": "cat-sat-hat",
    "host": "http://10.58.1.211:8532"
}
Note: if you are on a local machine
you may have to proxy into the live ArangoDB server first, e.g.,
`ssh -L 8532:10.58.1.211:8532 j_doe@login1.berkeley.kbase.us`
Then, the url would be `http://localhost:8532`
"""
    print(help_msg)
    raise

# Get pointer to collection
NCBI_TAXON = DB.collection("ncbi_taxon")

# Load the queries
QUERY = json_validation.load_json_yaml(STORED_QUERY_FP)["query"]
QUERY_NO_SORT = json_validation.load_json_yaml(STORED_QUERY_NO_SORT_FP)["query"]
QUERY_OLD = json_validation.load_json_yaml(STORED_QUERY_OLD_FP)["query"]

# Set query bind parameters
LIMIT = 20
NOW = time.time() * 1000

# Load/cache the scinames
# This probably won't work well and will need some fiddling/improvement
# because doing it this way can lead to a timeout on some machine setups
if os.path.isfile(SCINAMES_LATEST_FP):
    with open(SCINAMES_LATEST_FP) as fh:
        SCINAMES_LATEST = json.load(fh)
else:
    print("Fetching latest NCBI scinames ...")
    try:
        taxa_all = list(NCBI_TAXON.all())
    except ReadTimeout:
        print("Sorry, there is a read timeout. Please try again on a different machine")
        sys.exit()
    SCINAMES_LATEST = [
        taxa["scientific_name"]
        for taxa in taxa_all
        if (taxa["rank"] in ["species", "strain"] or taxa["strain"])
        and taxa["created"] <= NOW
        and NOW <= taxa["expired"]
    ]
    # Cache latest scinames
    with open(SCINAMES_LATEST_FP, "w") as fh:
        json.dump(SCINAMES_LATEST, fh)


def use_sort(search_text):
    """
    Determine whether to use the sorting or non-sorting stored query for the new query.
    Smaller search texts' results will not be sorted on.
    """
    return len(search_text) > 3


def is_simple(search_text):
    """
    Somewhat arbitrary determination of whether a fulltext's search text is "simple"
    relative to its search time
    """
    return len(search_text.split()) == 2 and all(
        [tok.isalnum() and len(tok) >= 3 for tok in search_text.split()]
    )


def jprint(jo, dry=False):
    txt = json.dumps(jo, indent=3)
    if dry:
        return txt
    else:
        print(txt)


def do_taxonomy_search_species_query(search_text):
    """Do the old query"""
    cursor = DB.aql.execute(
        QUERY_OLD,
        bind_vars={
            "@taxon_coll": "ncbi_taxon",
            "sciname_field": "scientific_name",
            "search_text": "prefix:" + search_text,  # how the old query was set up
            "ts": NOW,
            "offset": None,
            "limit": LIMIT,
            "select": ["scientific_name"],
        },
    )
    return {
        "results": [e["scientific_name"] for e in list(cursor.batch())],
        **cursor.statistics(),
    }


def do_taxonomy_search_species_strain_query(search_text):
    """Do the new query"""
    cursor = DB.aql.execute(
        QUERY if use_sort(search_text) else QUERY_NO_SORT,
        bind_vars={
            "@taxon_coll": "ncbi_taxon",
            "sciname_field": "scientific_name",
            "search_text": search_text,
            "ts": NOW,
            "offset": None,
            "limit": LIMIT,
            "select": ["scientific_name"],
        },
    )
    return {
        "results": [e["scientific_name"] for e in list(cursor.batch())],
        **cursor.statistics(),
    }


def get_search_text_samplings(
    resample=True,
    cap_scinames=1000,
    cap_scinames_prefixes=1000,
):
    """
    Get samplings of scinames or prefixes thereof to gauge execution time

    Things to include:
    * Simple genus/species epithets with two non-short words
    * "Wild" scientific names, defined as the exclusion of the simple scientific names
    * All prefixes of all the preceding, respectively, and deduplicated
    * 36 alphanumeric characters
    * Any edge cases?
    """
    # Read if cached
    if not resample and os.path.isfile(SAMPLINGS_FP):
        with open(SAMPLINGS_FP) as fh:
            samplings = json.load(fh)
        return samplings

    print("\nSampling search texts and prefixes thereof ...")

    def get_capped_samplings(styp: str) -> Tuple[list, list]:
        """
        Randomly sample scinames
        Then take all prefixes, deduplicated
        "Wild" just means the exclusion of "simple"
        """
        if styp not in ["simple", "wild"]:
            raise RuntimeError(f"Unknown sampling type {styp}")
        print(f"Sampling {styp} scinames ...")

        sampling = [
            sciname
            for sciname in SCINAMES_LATEST
            if is_simple(sciname) == (styp == "simple")
        ]
        random.shuffle(sampling)
        sampling = sampling[
            :cap_scinames
        ]  # cap this first to avoid generating overabundant prefixes

        sampling_prefixes = list(
            set([sciname[:i] for sciname in sampling for i in range(1, len(sciname))])
        )
        random.shuffle(sampling_prefixes)
        sampling_prefixes = sampling_prefixes[:cap_scinames_prefixes]

        return sampling, sampling_prefixes

    scinames_simple, scinames_simple_prefixes = get_capped_samplings("simple")
    scinames_wild, scinames_wild_prefixes = get_capped_samplings("wild")
    alphanum_chars = list("abcdefghijklmnopqrstuvwxyz0123456789")
    edge_cases = [
        "~!@#$%^&*()_+hi",
        "hi~!@#$%^&*()_+",
    ]  # would cause AQL issue: "", "~!@#$%^&*()_+", "[",

    # Aggregate
    samplings = {
        "scinames_simple": scinames_simple,
        "scinames_wild": scinames_wild,
        "scinames_simple_prefixes": scinames_simple_prefixes,
        "scinames_wild_prefixes": scinames_wild_prefixes,
        "alphanum_chars": alphanum_chars,
        "edge_cases": edge_cases,
    }

    # Manual peek to stdout
    peek_len = 10
    jprint(
        {
            styp: sampling[:peek_len] + (["..."] if len(sampling) > peek_len else [])
            for styp, sampling in samplings.items()
        }
    )

    # Cache samplings
    with open(SAMPLINGS_FP, "w") as fh:
        json.dump(samplings, fh)

    return samplings


def handle_err(msg, dat=None):
    """
    During sampling/sciname/query loops,
    if error arises,
    log/record
    """
    print(msg)
    tb.print_exc()
    if dat:
        dat["failed"] = True
        jprint(dat)


def update_print_timekeepers(i, t0, exe_times, sampling, num_failed):
    """
    Calculate and print
    * Running average time per iteration
    * Running average time per query execition
    * Running median time per query execution

    Precondition: t0, exe_times
    """
    if i == 0:
        tper_iter, tper_exe, tmed_exe, tmin_exe, tmax_exe = 0, 0, 0, 0, 0
    else:
        tper_iter = (time.time() - t0) / i
        tper_exe = np.nanmean(exe_times)
        tmed_exe = np.nanmedian(exe_times)
        tmin_exe = np.nanmin(exe_times)
        tmax_exe = np.nanmax(exe_times)
    print(
        f"[{datetime.datetime.now().strftime('%b%d %H:%M').upper()}]",
        "...",
        f"{i}/{len(sampling)} search texts tested",
        "...",
        f"{'%.3fs' % tmin_exe} (min)",
        "|",
        f"{'%.3fs' % tper_exe} (mean)",
        "|",
        f"{'%.3fs' % tmed_exe} (median)",
        "|",
        f"{'%.3fs' % tmax_exe} (max) exe time",
        "...",
        f"{'%.3fs' % tper_iter} per round trip",
        "...",
        f"{'%d/%d' % (num_failed, i)} failed",
    )


########################################################################################################################
########################################################################################################################
def do_query_testing(
    samplings: dict,
    do_query_func=do_taxonomy_search_species_strain_query,
    expect_hits: list = [
        "scinames_simple",
        "scinames_wild",
        "scinames_latest",
        "scinames_latest_permute",
    ],
    permute: bool = True,
    update_period: int = 100,
):
    """
    Test search texts, gather statistics, and check for hits
    Periodically outputs accumulated mean and median execution times
    """
    # Permute since the scinames tend to start out simpler
    if permute:
        for styp, sampling in samplings.items():
            samplings[styp] = sampling[:]
            random.shuffle(samplings[styp])

    # Get some nice stats to print out
    samplings_metadata = [
        {"styp": styp, "num": len(sampling)} for styp, sampling in samplings.items()
    ]
    total_num_queries = sum([len(sampling) for sampling in samplings.values()])

    # Print some preliminary info
    w = 120
    dec = "=" * w
    prelude = textwrap.wrap(
        (
            f"do_query_func={do_query_func.__name__}, "
            f"samplings_num_queries={samplings_metadata}, "
            f"total_num_queries={total_num_queries}, "
        ),
        width=w,
    )
    print("\n\n")
    print(dec)
    print(dec)
    print(*prelude, sep="\n")
    print(dec)
    print(dec)
    print()

    # Data structures accumulating all info
    data_all = dict()  # For all queries

    try:

        for j, (styp, sampling) in enumerate(samplings.items()):
            num_failed: int = 0
            data: List[dict] = []
            data_all[styp] = data

            t0 = time.time()  # Wall clock start time for this sampling
            exe_times: List[float] = []  # Query execution times for this sampling

            print(
                f"\nTesting with sampling_metadata={samplings_metadata[j]},",
                f"sampling_assert_hit={styp in expect_hits},",
                "...",
            )
            print(dec)

            # Traverse all samples in sampling
            for i, search_text in enumerate(sampling):
                # Calculate and print running time stats
                if not i % update_period:
                    update_print_timekeepers(i, t0, exe_times, sampling, num_failed)

                dat = {
                    "i": i,
                    "search_text": search_text,
                    "failed": False,
                }
                data.append(dat)

                try:
                    query_res = do_query_func(search_text)
                except Exception:
                    handle_err("Something went wrong in the query!", dat)
                    query_res = {
                        "execution_time": np.nan,
                        "results": [],
                    }

                exe_times.append(query_res["execution_time"])
                dat.update(query_res)

                # Set `has_results`
                dat["has_results"] = len(query_res["results"]) > 0
                # Set `failed`
                if styp in expect_hits:
                    hits = query_res["results"]
                    # Given that limit=20,
                    # test that sciname is in top 20,
                    # and they aren't >20 duplicates.
                    # Raise to get traceback in stdout
                    try:
                        assert search_text in hits  # nosec B101
                        assert not (  # nosec B101
                            len(hits) == LIMIT
                            and all([hit == search_text for hit in hits])
                        )
                    except AssertionError:
                        num_failed += 1
                        handle_err(
                            "Something went wrong in the expect hit assertion!",
                            dat,
                        )

            # One last time after all of sampling has run
            update_print_timekeepers(i + 1, t0, exe_times, sampling, num_failed)

    except Exception:
        handle_err("Something went wrong in the samplings/scinames/query loops!")

    finally:
        results_fp = os.path.join(
            TMP_OUT_DIR,
            (
                "res"
                "__"
                f"{datetime.datetime.now().strftime('%d%b%Y_%H:%M').upper()}"
                "__"
                f"{do_query_func.__name__}"
                "__"
                f"{len(samplings)}_samplings"
                "__"
                f"{total_num_queries}_search_texts"
                ".json"
            ),
        )
        data_meta = {
            "do_query_func": do_query_func.__name__,
            "samplings": list(samplings.keys()),
            "expect_hits": expect_hits,
            "total_num_queries": total_num_queries,
            "_sampling": styp,  # where it may have
            "_i": i,  # stopped at
            "data_all": data_all,
        }
        print(dec)
        print(f"\nWriting results to {results_fp}")
        print(dec)
        with open(results_fp, "w") as fh:
            json.dump(data_meta, fh, indent=3)

        return data_meta


########################################################################################################################
########################################################################################################################
@pytest.mark.skipif(
    not os.environ.get("DO_QUERY_TESTING") == "full",
    reason="This can take a couple days, and only needs to be ascertained sporadically",
)
def test_all_ncbi_latest_scinames():
    do_query_testing({"scinames_latest": SCINAMES_LATEST})


@pytest.mark.skipif(
    not os.environ.get("DO_QUERY_TESTING") == "sampling",
    reason="This can take an hour or so, and only needs to be ascertained sporadically",
)
def test_samplings():
    do_query_testing(
        samplings=get_search_text_samplings(resample=True),
        do_query_func=do_taxonomy_search_species_strain_query,
    )


@pytest.mark.skipif(
    not os.environ.get("DO_QUERY_TESTING") == "compare",
    reason="This can take an hour or so, and only needs to be ascertained sporadically",
)
def test_compare_queries():
    do_query_testing(
        samplings=get_search_text_samplings(
            resample=True, cap_scinames=500, cap_scinames_prefixes=500
        ),
        do_query_func=do_taxonomy_search_species_strain_query,
        permute=False,
    )
    do_query_testing(
        samplings=get_search_text_samplings(resample=False),
        do_query_func=do_taxonomy_search_species_query,
        permute=False,
    )


def do_graph(data_new_fp, data_old_fp):
    """
    {
        "data_all": {
            "styp0": [
                {
                    "i": int,  # index in sampling
                    "search_text": str,
                    "failed": bool,
                    "results": [  # resulting scinames
                        ...
                    ],
                    "execution_time": float,  # s
                    ...
                },
                ...
            ],
            "styp1": [
                ...
            ],
            ...
        },
        ...
    }
    """
    with open(data_new_fp) as fh:
        data_new = json.load(fh)["data_all"]
    with open(data_old_fp) as fh:
        data_old = json.load(fh)["data_all"]

    # Not meaningful/large enough to make the figure
    if "edge_cases" in data_new:
        del data_new["edge_cases"]
    if "edge_cases" in data_old:
        del data_old["edge_cases"]

    # Count num queries where the old stored query `has_results`/`failed`
    old_failed_counts = {
        styp: (
            len([1 for dat in data if not dat["failed"]]),
            len([1 for dat in data if dat["failed"]]),
        )
        for styp, data in data_old.items()
    }
    old_has_results_counts = {
        styp: (
            len([1 for dat in data if not dat["results"]]),
            len([1 for dat in data if dat["results"]]),
        )
        for styp, data in data_old.items()
    }

    # Sanity checks
    # Should have same ordering in `styp` and `search_text`
    for (styp0, data0), (styp1, data1) in zip(data_new.items(), data_old.items()):
        assert styp0 == styp1  # nosec B101
        assert len(data0) == len(data1)  # nosec B101
        for dat0, dat1 in zip(data0, data1):
            assert dat0["search_text"] == dat1["search_text"]  # nosec B101
            assert not np.isnan(dat0["execution_time"])  # nosec B101
            assert not np.isnan(dat1["execution_time"])  # nosec B101
    # old_has_results and old_failed counts should add up
    for counts in [old_failed_counts, old_has_results_counts]:
        for styp, count in counts.items():
            assert sum(count) == len(data_old[styp])  # nosec B101

    df_data = []
    df_columns = [
        "exe_time_ms",
        "stored_query",
        "sampling",
        "failed",
        "has_results",
        "old_failed",
        "old_has_results",
    ]
    for sq, data_epoch in zip(["new", "old"], [data_new, data_old]):
        for styp, data in data_epoch.items():
            for i, dat in enumerate(data):
                # Toggle the literal strings here in tandem with
                # toggling the `hue` below
                df_row = [
                    int(dat["execution_time"] * 1000),
                    sq,
                    f"{styp}\nn = {len(data)} ({old_failed_counts[styp][0]}/{old_failed_counts[styp][1]})",
                    # f"{styp}\nn = {len(data)} ({old_has_results_counts[styp][0]}/{old_has_results_counts[styp][1]})",
                    dat["failed"],
                    dat["has_results"],
                    data_old[styp][i]["failed"],
                    data_old[styp][i]["has_results"],
                ]
                df_data.append(df_row)

    df = pd.DataFrame(df_data, columns=df_columns)

    sns.catplot(
        x="stored_query",
        y="exe_time_ms",
        hue="old_failed",  # Toggle the `hue` here in tandem with
        # hue="old_has_results",     # toggling the literal strings n `df_row` above
        scale="area",
        scale_hue=False,
        col="sampling",
        data=df,
        kind="violin",
        split=True,
        cut=0,
        aspect=0.7,
        bw=0.2,
    )

    plt.show()


if __name__ == "__main__":
    do_graph(sys.argv[1], sys.argv[2])
