import traceback as tb
import sys
import os
import json
import datetime
import time
import random
import textwrap
import warnings
import pytest
from typing import Tuple, List
from requests.exceptions import ReadTimeout

from arango import ArangoClient
import numpy as np

from relation_engine_server.utils import json_validation

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
    ROOT_DIR, "spec/stored_queries/taxonomy/taxonomy_ncbi_species.yaml"
)
STORED_QUERY_NO_SORT_FP = os.path.join(
    ROOT_DIR, "spec/stored_queries/taxonomy/taxonomy_ncbi_species_no_sort.yaml"
)

if not os.path.exists(TMP_OUT_DIR):
    os.mkdir(TMP_OUT_DIR)

try:
    with open(CONFIG_FP) as fh:
        CONFIG = json.load(fh)
    if not CONFIG["host"] or not CONFIG["username"] or not CONFIG["password"]:
        raise RuntimeError("Missing config fields")
    CLIENT = ArangoClient(hosts=CONFIG["host"])
    DB = CLIENT.db("ci", username=CONFIG["username"], password=CONFIG["password"])
except Exception as e:
    help = """
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
    print(help)
    raise (e)
NCBI_TAXON = DB.collection("ncbi_taxon")

# Load the queries
QUERY = json_validation.load_json_yaml(STORED_QUERY_FP)["query"]
QUERY_NO_SORT = json_validation.load_json_yaml(STORED_QUERY_NO_SORT_FP)["query"]

LIMIT = 20
NOW = time.time() * 1000

# Load/cache the scinames
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
    with open(SCINAMES_LATEST_FP, "w") as fh:
        json.dump(SCINAMES_LATEST, fh)


def use_sort(search_text):
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


def fulltext_search_ncbi_scinames(search_text):
    """"""
    cursor = DB.aql.execute(
        QUERY if use_sort(search_text) else QUERY_NO_SORT,
        bind_vars={
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
    cap_scinames=2000,
    cap_scinames_prefixes=5000,
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

    print("Sampling search texts and prefixes thereof ...")

    seen_prefixes = set()

    def get_capped_samplings(styp: str) -> Tuple[list, list]:
        """
        Randomly sample scinames
        Then take all prefixes (not already seen in accumulated prefixes)
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
        sampling = sampling[:cap_scinames]
        sampling_prefixes = [
            sciname[:i] for sciname in sampling for i in range(1, len(sciname))
        ]
        sampling_prefixes = [
            sciname
            for sciname in sampling_prefixes
            if sciname not in seen_prefixes
            and not seen_prefixes.add(
                sciname
            )  # latter operand always evaluates to true
        ]
        return sampling, sampling_prefixes[:cap_scinames_prefixes]

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


def handle_err(msg, dat, failed):
    """
    During sampling/sciname/query loops,
    if error arises,
    log/record
    """
    print(msg)
    tb.print_exc()
    jprint(dat)
    failed.append(dat)


def update_print_timekeepers(i, t0, exe_times, sampling, failed):
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
        tper_exe = np.mean(exe_times)
        tmed_exe = np.median(exe_times)
        tmin_exe = np.min(exe_times)
        tmax_exe = np.max(exe_times)
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
        f"{'%d/%d' % (len(failed), i)} failed",
    )


################################################################################
################################################################################
def do_query_testing(
    samplings: dict,
    expect_hits: list = [
        "scinames_simple",
        "scinames_wild",
        "scinames_latest",
        "scinames_latest_permute",
    ],
    update_period: int = 100,
):
    """
    Test search texts, gather statistics, and check for hits
    Periodically outputs accumulated mean and median execution times
    """
    # Permute since the scinames tend to start out simpler
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
        "\n".join(
            [
                f"samplings_num_queries={samplings_metadata},",
                f"total_num_queries={total_num_queries},",
            ]
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
    failed_all = dict()  # For failed queries

    try:

        for j, (styp, sampling) in enumerate(samplings.items()):
            failed: List[dict] = []
            failed_all[styp] = failed
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
                    update_print_timekeepers(i, t0, exe_times, sampling, failed)

                dat = {
                    "styp": styp,
                    "i": i,
                    "search_text": search_text,
                }
                data.append(dat)

                try:
                    query_res = fulltext_search_ncbi_scinames(search_text)
                except Exception:
                    handle_err("Something went wrong in the query!", dat, failed)

                exe_times.append(query_res["execution_time"])
                dat.update(query_res)

                if styp in expect_hits:
                    try:
                        hits = query_res["results"]
                        # Given that limit=20,
                        # test that sciname is in top 20,
                        # and they aren't >20 duplicates.
                        # Raise to get traceback in stdout
                        if search_text not in hits or (
                            len(hits) == LIMIT
                            and all([hit == search_text for hit in hits])
                        ):
                            raise AssertionError(
                                "Target sciname not in results "
                                "or results are all duplicates"
                            )
                    except AssertionError:
                        handle_err(
                            "Something went wrong in the expect hit assertion!",
                            dat,
                            failed,
                        )

            # One last time after all of sampling has run
            update_print_timekeepers(i + 1, t0, exe_times, sampling, failed)

    except Exception:
        handle_err(
            "Something went wrong in the samplings/scinames/query loops!", dat, failed
        )

    finally:
        results_fp = os.path.join(
            TMP_OUT_DIR,
            (
                "res"
                "__"
                f"{datetime.datetime.now().strftime('%d%b%Y_%H:%M').upper()}"
                "__"
                f"{len(samplings)}_samplings"
                "__"
                f"{total_num_queries}_search_texts"
                ".json"
            ),
        )
        data_meta = {
            "samplings": list(samplings.keys()),
            "expect_hits": expect_hits,
            "total_num_queries": total_num_queries,
            "sampling": styp,
            "i": i,
            "data_all": data_all,
            "failed_all": failed_all,
        }
        print(f"\nWriting results/failures to {results_fp}")
        with open(results_fp, "w") as fh:
            json.dump(data_meta, fh, indent=3)

        return data_meta


@pytest.mark.skipif(
    not os.environ.get("DO_QUERY_TESTING") == "full",
    reason="This can take a couple days, and only needs to be ascertained once",
)
def test_all_ncbi_latest_scinames():
    do_query_testing({"scinames_latest": SCINAMES_LATEST})


@pytest.mark.skipif(
    not os.environ.get("DO_QUERY_TESTING") == "sampling",
    reason="This can take a few hours, and only needs to be ascertained once",
)
def test_samplings():
    do_query_testing(get_search_text_samplings())
