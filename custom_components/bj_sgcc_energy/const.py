DOMAIN = "bj_sgcc_energy"

PGC_PRICE = {
    "climax": {
        "key": "尖峰",
        "month": [7, 8],
        "time_slot": [[11, 13], [16, 17]]
    },
    "peak": {
        "key": "峰",
        "time_slot": [[10, 15], [18, 21]]
    },
    "ground": {
        "key": "平",
        "time_slot": [[7, 10], [15, 18], [21, 23]]
    },
    "valley": {
        "key": "谷",
        "time_slot": [[23, 7]]
    }
}