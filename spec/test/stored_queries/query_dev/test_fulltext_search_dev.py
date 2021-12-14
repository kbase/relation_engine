import os
import json
import datetime
import time
import random
import textwrap
import gzip
import json
import functools
import gzip
import warnings
import random
import os
import requests
import pytest

from arango import ArangoClient
import matplotlib.pyplot as plt
import numpy as np

from spec.test.helpers import get_arango_config
from relation_engine_server.utils import (
    arango_client,
    spec_loader,
)

warnings.filterwarnings("ignore")


arango_config = get_arango_config()
username = arango_config["username"]
password = arango_config["password"]
host_url = arango_config["host_url"]

client = ArangoClient(hosts=host_url)
db = client.db("ci", username=username, password=password)
ncbi_taxon = db.collection("ncbi_taxon")
gtdb_taxon = db.collection("gtdb_taxon")
silva_taxon = db.collection("silva_taxon")
# ncbi_taxon_all = list(ncbi_taxon.all())

LIMIT = 20  # query ret
TS = 1636586429084  # ms. NOV 2021

CAP_SCINAMES = 2000
CAP_SCINAMES_PREFIXES = 5000


# Assuming running the file
if "__file__" in globals():
    TEST_DATA_DIR = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/")
    )
# Assuming running the code from repo home
else:
    TEST_DATA_DIR = os.path.join(os.getcwd(), "src/test/data/")

TMP_OUT_DIR = os.path.join(TEST_DATA_DIR, "tmp_out")
if not os.path.exists(TMP_OUT_DIR):
    os.mkdir(TMP_OUT_DIR)
scinames_all_fp = os.path.join(
    TEST_DATA_DIR, "ncbi_taxon__scientific_names__NOV_2021__all.json.gz"
)
scinames_latest_fp = os.path.join(
    TEST_DATA_DIR, "ncbi_taxon__scientific_names__NOV_2021__latest.json.gz"
)
with gzip.open(scinames_latest_fp, "rb") as fh:
    scinames_latest = json.load(fh)

    scinames_latest_permute = scinames_latest[:]
    random.shuffle(scinames_latest_permute)


def is_simple_sciname(sciname):
    return len(sciname.split()) == 2 and all(
        [tok.isalnum() and len(tok) >= 3 for tok in sciname.split()]
    )


def pprint(jo, dry=False):
    txt = json.dumps(jo, indent=3)
    if dry:
        return txt
    else:
        print(txt)


def fulltext_raw(search_text, query=FULLTEXT_QUERY):
    cursor = db.aql.execute(
        query,
        bind_vars={
            "@coll": "ncbi_taxon",
            "search_attrkey": "scientific_name",
            "search_text": search_text,
            "filter_attr_expr": [{"rank": "species"}, {"strain": True}],
            "ts": TS,
            "offset": None,
            "limit": LIMIT,
            "select": ["scientific_name"],
        },
    )
    return {**next(cursor), **cursor.statistics()}


def get_search_text_samplings(
    scinames_latest_fp=scinames_latest_fp,
    out_samplings_fn="samplings.json",
    cap_scinames=CAP_SCINAMES,
    cap_scinames_prefixes=CAP_SCINAMES_PREFIXES,
):
    """
    Get sample search texts to compare the one fulltext query against other(s)

    Things to include:
    * Simple genus/species epithets with two non-short words
    * "Wild" scientific names that are the exclusion of the simple scientific names
    * All prefixes of the preceding, deduplicated, but also still associated with respective origin sampling group
    * 36 alphanumeric characters
    * Any edge cases?
    """
    with gzip.open(scinames_latest_fp, "rb") as fh:
        scinames = json.load(fh)

    seen_prefixes = set()

    def get_capped_samplings(styp):
        """
        Randomly sample scinames
        Then take all prefixes (not already seen in accumulated prefixes)
        "Wild" just means the exclusion of "simple"
        """
        assert styp in ["simple", "wild"]
        print(f"Sampling {styp} scinames ...")

        sampling = [
            sciname
            for sciname in scinames
            if is_simple_sciname(sciname) == (styp == "simple")
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
    edge_cases = ["", "~!@#$%^&*()_+", "~!@#$%^&*()_+hi", "hi~!@#$%^&*()_+", "[", None]

    # Aggregate
    samplings = {
        "scinames_simple": scinames_simple,
        "scinames_wild": scinames_wild,
        "scinames_simple_prefixes": scinames_simple_prefixes,
        "scinames_wild_prefixes": scinames_wild_prefixes,
        "alphanum_chars": alphanum_chars,
        "edge_cases": edge_cases,
    }

    # Manual peek
    peek_len = 50
    print(
        json.dumps(
            {
                styp: sampling[:peek_len]
                + (["..."] if len(sampling) > peek_len else [])
                for styp, sampling in samplings.items()
            },
            indent=3,
        )
    )

    with open(os.path.join(TMP_OUT_DIR, out_samplings_fn), "w") as fh:
        json.dump(samplings, fh)
    return samplings


################################################################################
################################################################################
@pytest.mark.skipif(
    not os.environ.get("RUN_FULLTEXT_SEARCH_DEV"),
    reason="This can take a few hours to a few days, and only needs to be ascertained once",
)
def test_fulltext_scinames(
    samplings={
        "scinames_latest_permute": scinames_latest_permute[:CAP_SCINAMES],
        # **get_search_text_samplings(),
    },
    queries={"new": spec_loader.get_stored_query("fulltext_search")},  # queries,
    expect_hits={
        "samplings": [
            "scinames_simple",
            "scinames_wild",
            "scinames_latest",
            "scinames_latest_permute",
        ],
        "queries": ["new"],
    },
    update_period=100,
):
    """
    On default settings, will test all latest scinames (capped), simple scinames (capped), non-simple scinames(capped),
    prefixes thereof (capped), single alphanumeric characters, and some edge cases. This will occur with "old"
    and "new" queries. This is to compare perfomance, mostly by average and median execution times.

    Can also
    * Test other samplings (other than all latest scinames) and toggle whether to check for hits
    * Test other queries (other than "new") and toggle whether to check for hits
    """
    # Permute
    for styp, sampling in samplings.items():
        samplings[styp] = sampling[:]
        random.shuffle(samplings[styp])
    total_scinames = sum([len(sampling) for sampling in samplings.values()])
    samplings_metadata = [
        {"styp": styp, "num": len(sampling)} for styp, sampling in samplings.items()
    ]

    w = 150
    dec = "=" * w
    prelude = textwrap.wrap(
        "\n".join(
            [
                f"Testing samplings={samplings_metadata},",
                f"total_scinames={total_scinames},",
                f"queries={list(queries.keys())},",
                f"expect_hits={expect_hits},",
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

    data_all = dict()
    failed_all = dict()

    try:

        def handle_err(e, msg, dat):
            """
            During sampling/sciname/query loops,
            if error arises,
            log/record
            """
            print(msg)
            print(e)
            pprint(dat)
            failed.append(dat)

        for k, (styp, sampling) in enumerate(samplings.items()):
            failed = []
            failed_all[styp] = failed
            data = []
            data_all[styp] = data

            t0 = time.time()
            qtyp_2_exe_times = {qtyp: [] for qtyp in queries.keys()}

            def update_timekeepers_print(i):
                """
                Precondition: t0, qtyp_2_exe_times
                """
                tper_iter = 0 if i == 0 else (time.time() - t0) / i
                tper_exes = {
                    qtyp: np.mean(exe_times)
                    for qtyp, exe_times in qtyp_2_exe_times.items()
                }
                tmed_exes = {
                    qtyp: np.median(exe_times)
                    for qtyp, exe_times in qtyp_2_exe_times.items()
                }
                print(
                    "...",
                    f"[{datetime.datetime.now().strftime('%b%d %H:%M').upper()}]",
                    "...",
                    f"Tested {i}/{len(sampling)} search texts",
                    "...",
                    f"{ {qtyp: '%.3fs' % tper_exe for qtyp, tper_exe in tper_exes.items()}} per search text (mean exe time)",
                    "...",
                    f"{ {qtyp: '%.3fs' % tmed_exe for qtyp, tmed_exe in tmed_exes.items()}} per search text (median exe time)",
                    "...",
                    f"{'%.3fs' % tper_iter} per search text iteration",
                    "...",
                )
                return tper_iter, tper_exes, tmed_exes

            print(
                f"\nTesting sampling={samplings_metadata[k]},",
                f"queries={list(queries.keys())},",
                f'sampling_assert_hit={styp in expect_hits["samplings"]},',
                f'queries_assert_hit={expect_hits["queries"] if styp in expect_hits["samplings"] else []}',
                "...",
            )
            print(dec)
            for i in range(len(sampling)):
                # Time stats from all previous iterations
                if not i % update_period:
                    tper_iter, tper_exes, tmed_exes = update_timekeepers_print(i)

                sciname = sampling[i]
                for qtyp, query in queries.items():
                    dat = {
                        "styp": styp,
                        "qtyp": qtyp,
                        "i": i,
                        "sciname": sciname,
                        "is_simple_sciname": is_simple_sciname(sciname),
                        # --------- from previous iters, updated intermittently  ---------- #
                        "tper_py": tper_iter,
                        "tper_exe": tper_exes[qtyp],
                        "tmed_exe": tmed_exes[qtyp],
                        "fail_rate": f"{len(failed)}/{i + 1}",
                    }
                    data.append(dat)

                    try:
                        query_res = fulltext_raw(sciname, query=query)
                    except Exception as e:
                        handle_err(e, "Something went wrong in the query!", dat)

                    qtyp_2_exe_times[qtyp].append(query_res["execution_time"])
                    dat.update(query_res)

                    if (
                        styp in expect_hits["samplings"]
                        and qtyp in expect_hits["queries"]
                    ):
                        try:
                            res_scinames = dat["res_scinames"]
                            # Given that limit=20,
                            # test that sciname is in top 20,
                            # and they aren't possibly >20 duplicates
                            assert sciname in res_scinames and not (
                                len(res_scinames) == LIMIT
                                and all(
                                    [
                                        res_sciname == sciname
                                        for res_sciname in res_scinames
                                    ]
                                )
                            )
                        except AssertionError as e:
                            handle_err(
                                e,
                                "Something went wrong in the expect hit assertion!",
                                dat,
                            )

        tper_iter, tper_exes, tmed_exes = update_timekeepers_print(i + 1)

    except Exception as e:
        handle_err(
            e, "Something went wrong in the samplings/scinames/query loops!", dat
        )

    finally:
        results_fp = os.path.join(
            TMP_OUT_DIR,
            (
                "res__"
                f"{datetime.datetime.now().strftime('%d%b%Y_%H:%M').upper()}__"
                f"{i}_of_{total_scinames}_scinames__"
                f"{k}_of_{len(samplings)}_samplings__"
                f"{len(queries)}_queries__"
                f"{'latest' if TS else 'all'}_ts"
                ".json"
            ),
        )
        data_all = {
            "i": i,
            "samplings": list(samplings.keys()),
            "total_scinames": total_scinames,
            "queries": list(queries.keys()),
            "expect_hits": expect_hits,
            "ts": TS,
            "limit": LIMIT,
            "data_all": data_all,
            "failed_all": failed_all,
        }
        print(f"\nWriting results/failures to {results_fp}")
        with open(results_fp, "w") as fh:
            json.dump(data_all, fh, indent=3)

        return data_all


################################################################################
################################################################################
def check_fulltext_scinames(results_fp, fig_dir):
    """
    Do some light graphing

    The execution times are capped off at 1000ms when all tok lens are gte 1
    The execution times are capped off at 1750ms when all tok lens are gte 2
    The execution times are drastically capped off, to ~200ms, when all tok lens are gte 3 (***)
    The execution times are subsequently halved, to ~100ms, when all tok lens are gte 6

    Weak relationship between number of tokens and execution time
    Num toks len lte 1 doesn't predict execution time well
    Num toks len lte 2 suddenly shows a pattern: f(0)=(0,250), f(1)=(0,1250), f(2)=(0,2000), f(3)=(0,2250), dodgy afterwards
    Num toks len lte 3 doesn't provide much more information, just shifts some points to the right with the 3-len toks
    Num toks len lte 4 ... same

    Conclusion: The short/problematic tokens that cause a significant jump in execution time are length 1 and 2
    """

    def scatter(x, y, fn):
        plt.figure()
        plt.xlabel("num_toks")
        plt.ylabel("exe_time")
        plt.suptitle(fn)
        plt.scatter(x, y)
        plt.savefig(os.path.join(fig_dir, fn))
        plt.close()

    with open(results_fp) as fh:
        results = json.load(fh)["data_all"]["latest_scinames"]

    toks_l = [res["search_text__wordboundmod_icu_toks"][:] for res in results]
    tok_lens_l = [[len(tok) for tok in toks] for toks in toks_l]
    num_toks = [len(toks) for toks in toks_l]

    # -------------------------------------------------------------

    vecs = {
        "num_toks": num_toks,
        "num_toks_len_lte1": [
            sum([tok_len <= 1 for tok_len in tok_lens]) for tok_lens in tok_lens_l
        ],
        "num_toks_len_lte2": [
            sum([tok_len <= 2 for tok_len in tok_lens]) for tok_lens in tok_lens_l
        ],
        "num_toks_len_lte3": [
            sum([tok_len <= 3 for tok_len in tok_lens]) for tok_lens in tok_lens_l
        ],
        "num_toks_len_lte4": [
            sum([tok_len <= 4 for tok_len in tok_lens]) for tok_lens in tok_lens_l
        ],
        "num_toks_len_lte5": [
            sum([tok_len <= 5 for tok_len in tok_lens]) for tok_lens in tok_lens_l
        ],
        "exe_time": [float(res["execution_time"]) * 1000 for res in results],
    }

    print("Scattering num_toks and num_toks_lte_x ...")

    for vec_name, vec in vecs.items():
        if vec_name == "exe_time":
            continue
        scatter(vec, vecs["exe_time"], vec_name)

    # -------------------------------------------------------------

    def keep_all_tok_lens_gte(length: int):
        inds = [
            i
            for i, tok_lens in enumerate(tok_lens_l)
            if all([tok_len >= length for tok_len in tok_lens])
        ]

        x = np.array(vecs["num_toks"])[inds]
        y = np.array(vecs["exe_time"])[inds]

        return x, y

    print("Scattering num_toks__when_all_len_gte_x ...")

    for length in [1, 2, 3, 4, 5, 6, 7]:
        x, y = keep_all_tok_lens_gte(length)
        scatter(x, y, f"num_toks__when_all_len_gte{length}")
