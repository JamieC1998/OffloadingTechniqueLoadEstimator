import pickle
import os
import itertools
from itertools import product, permutations
from datetime import timedelta as td
from typing import List, Set, Dict
from datetime import datetime as dt
import json

model_folder = "./model_bench"

part_config_file_name = "data_sizes.pkl"
proc_times_file_name = "proc_times.pkl"


def data_main():
    bits_ps = 55947313.60676045
    jitter = 11301312.582474127
    bytes_per_second = (bits_ps - jitter) / 8
    models = [model for model in os.listdir(model_folder) if model != ".DS_store"]

    cores_per_device = 4
    devices_in_network = 4

    results_dict = {
        key: {"ftp": {}, "ftp_no_comm": {}, "no_part": {}, "multisplit": {}}
        for key in models
    }

    for model in models:
        dir_prefix = f"{model_folder}/{model}"
        part_config_file_path = f"{dir_prefix}/{part_config_file_name}"
        proc_times_file_path = f"{dir_prefix}/{proc_times_file_name}"
        part_config_file = open(part_config_file_path, "rb")
        proc_times_file = open(proc_times_file_path, "rb")

        part_config_data = pickle.load(part_config_file)
        proc_times_data = pickle.load(proc_times_file)

        part_config_file.close()
        proc_times_file.close()

        results_dict[model]["ftp"] = basic_FTP_comp_vs_comm(
            data_size_config=part_config_data,
            processing_time_config=proc_times_data,
            bytes_per_second=bytes_per_second,
            device_count=devices_in_network,
            core_per_device=cores_per_device,
        )
        results_dict[model]["ftp_no_comm"] = offload_no_vert(
            data_size_config=part_config_data,
            processing_time_config=proc_times_data,
            bytes_per_second=bytes_per_second,
            device_count=devices_in_network,
            partition_value=cores_per_device,
        )
        results_dict[model]["no_part"] = offload_no_vert(
            data_size_config=part_config_data,
            processing_time_config=proc_times_data,
            bytes_per_second=bytes_per_second,
            device_count=devices_in_network,
            partition_value=1,
        )
        results_dict[model]["multisplit"] = multi_split_vert_no_horizontal(
            data_size_config=part_config_data,
            processing_time_config=proc_times_data,
            bytes_per_second=bytes_per_second,
            device_count=devices_in_network,
        )

        results_dict[model]["single_split"] = single_split_vert_and_hori(
            data_size_config=part_config_data,
            processing_time_config=proc_times_data,
            bytes_per_second=bytes_per_second,
            device_count=devices_in_network,
            partition_value=1,
        )
        results_dict[model]["single_vert_horizontal"] = single_split_vert_and_hori(
            data_size_config=part_config_data,
            processing_time_config=proc_times_data,
            bytes_per_second=bytes_per_second,
            device_count=devices_in_network,
            partition_value=cores_per_device,
        )

    return results_dict


def multi_split_vert_no_horizontal(
    data_size_config: Dict,
    processing_time_config: Dict,
    bytes_per_second: float,
    device_count: int,
) -> Dict:
    computation_time: td = td()
    communication_time: td = td()

    conv_blocks = list(data_size_config.keys())
    conv_blocks.append(None)

    list_a = [[conv_blocks[0]]] + (
        [[item for item in conv_blocks]] * (device_count - 1)
    )

    all_combinations = list(product(*list_a))

    # Generate all permutations of the valid combinations
    permutations_set = all_combinations

    results_dict = {
        str(val): multisplit_basic_sim(
            data_size_config=data_size_config,
            processing_time_config=processing_time_config,
            bytes_per_second=bytes_per_second,
            offsets=val,
        )
        for val in permutations_set
    }

    sum_proc_times = 0
    for blocks in processing_time_config.keys():
        sum_proc_times = (
            sum_proc_times
            + processing_time_config[blocks][1]["mean"]
            + processing_time_config[blocks][1]["stdev"]
        )

    td_proc = td(seconds=sum_proc_times)

    return {"comp": td_proc, "comm": results_dict}


def multisplit_basic_sim(
    data_size_config: Dict,
    processing_time_config: Dict,
    bytes_per_second: float,
    offsets: Set,
) -> td:

    initial_time = dt.now()
    current_time = dt.now()
    start_times = [None] * 4

    actual_start_times = []
    actual_finish_times = [None] * 4

    network_link = []

    for i in range(len(offsets)):
        if i == 0:
            current_time = initial_time
        else:
            if offsets[i] != None:
                current_time = start_times[i - 1]
        actual_start_times.append(current_time)
        for blocks in data_size_config.keys():
            if i != len(offsets) - 1 and blocks == offsets[i + 1]:
                start_times[i] = current_time

            network_link, return_window = find_earliest_link_slot(
                current_time=current_time,
                estimated_time_window=td(
                    seconds=data_size_config[blocks][1]["totalsize"] / bytes_per_second
                ),
                network_link=network_link,
            )

            current_time = return_window[1] + td(
                seconds=processing_time_config[blocks][1]["mean"]
                + processing_time_config[blocks][1]["stdev"]
            )
            actual_finish_times[i] = return_window[1]
        continue

    sum_proc_times = 0
    sum_proc_times_no_last_block = 0
    for i in range(len(processing_time_config.keys())):

        sum_proc_times = (
            sum_proc_times
            + processing_time_config[i + 1][1]["mean"]
            + processing_time_config[i + 1][1]["stdev"]
        )
        if i < len(processing_time_config.keys()) - 1:
            sum_proc_times_no_last_block = (
                sum_proc_times_no_last_block
                + processing_time_config[i + 1][1]["mean"]
                + processing_time_config[i + 1][1]["stdev"]
            )

    td_proc = td(seconds=sum_proc_times)
    td_proc_no_last_block = td(seconds=sum_proc_times_no_last_block)

    comm_list = [
        (actual_finish_times[i] - actual_start_times[i]) - td_proc_no_last_block
        for i in range(len(actual_finish_times))
    ]

    return comm_list[len(comm_list) - 1]


def find_earliest_link_slot(
    current_time: dt, estimated_time_window: td, network_link: List
):

    return_window = []
    if len(network_link) == 0:
        network_link.append([current_time, current_time + estimated_time_window])
        return_window = [current_time, current_time + estimated_time_window]
    elif len(network_link) == 1:
        if current_time + estimated_time_window < network_link[0][0]:
            network_link.insert(0, [current_time, current_time + estimated_time_window])
            return_window = [current_time, current_time + estimated_time_window]
        else:
            floor = (
                current_time
                if current_time >= network_link[0][1]
                else network_link[0][1]
            )
            network_link.append([floor, floor + estimated_time_window])
            return_window = [floor, floor + estimated_time_window]
    else:
        if current_time + estimated_time_window < network_link[0][0]:
            network_link.insert(0, [current_time, current_time + estimated_time_window])
            return_window = [current_time, current_time + estimated_time_window]
        else:
            placement_found = False
            netlink_length = len(network_link)
            for i in range(netlink_length):
                if i < len(network_link) - 1:
                    floor = (
                        current_time
                        if current_time >= network_link[i][1]
                        else network_link[i][1]
                    )
                    if floor + estimated_time_window < network_link[i + 1][0]:
                        network_link.insert(
                            i + 1, [floor, floor + estimated_time_window]
                        )
                        return_window = [floor, floor + estimated_time_window]
                        placement_found = True
                        break

            if not placement_found:
                floor = (
                    current_time
                    if current_time >= network_link[len(network_link) - 1][1]
                    else network_link[len(network_link) - 1][1]
                )
                network_link.append([floor, floor + estimated_time_window])
                return_window = [floor, floor + estimated_time_window]

    return network_link, return_window


def single_split_vert_and_hori(
    data_size_config: Dict,
    processing_time_config: Dict,
    bytes_per_second: float,
    device_count: int,
    partition_value: int,
) -> Dict:

    computation_time: td = td(
        seconds=sum(
            [
                processing_time_config[key][
                    ftp_fetch_highest_partition_conf_per_block(
                        block_data_size_config=data_size_config[key],
                        max_core_conf=partition_value,
                    )
                ]["mean"]
                + processing_time_config[key][
                    ftp_fetch_highest_partition_conf_per_block(
                        block_data_size_config=data_size_config[key],
                        max_core_conf=partition_value,
                    )
                ]["stdev"]
                for key in processing_time_config.keys()
            ]
        )
    )

    transformed_data_list = [
        (conv, block_data[1]["totalsize"] / bytes_per_second)
        for conv, block_data in data_size_config.items()
    ]
    transformed_data_list.append((None, 0))

    lists = []

    for i in range(1, device_count):
        lists.append([(i, val) for val in transformed_data_list])

    lists.append(
        [(device_count, val) for val in transformed_data_list if val[0] != None]
    )

    # Get all permutations of elements across the lists
    perms = list(itertools.product(*lists))

    result_dict = {key[0]: [] for key in transformed_data_list if key[0] != None}

    for permutation in perms:
        for perm_item in permutation:
            if perm_item[0] == 4:
                result_dict[perm_item[1][0]].append(
                    [
                        item[1][1]
                        for item in permutation
                        if item[0] != 4 and item[1][0] != None
                    ]
                )

    result_dict = {
        key: set(
            td(
                seconds=(sum(value_list) if len(value_list) != 0 else 0)
                + data_size_config[key][1]["totalsize"] / bytes_per_second
            )
            for value_list in value_sets
        )
        for key, value_sets in result_dict.items()
    }
    result_dict = {key: sorted(value) for key, value in result_dict.items()}

    return {"comp": computation_time, "comm": result_dict}


def offload_no_vert(
    data_size_config: Dict,
    processing_time_config: Dict,
    bytes_per_second: float,
    device_count: int,
    partition_value: int,
) -> Dict:
    computation_time: td = td(
        seconds=sum(
            [
                processing_time_config[key][
                    ftp_fetch_highest_partition_conf_per_block(
                        block_data_size_config=data_size_config[key],
                        max_core_conf=partition_value,
                    )
                ]["mean"]
                + processing_time_config[key][
                    ftp_fetch_highest_partition_conf_per_block(
                        block_data_size_config=data_size_config[key],
                        max_core_conf=partition_value,
                    )
                ]["stdev"]
                for key in processing_time_config.keys()
            ]
        )
    )

    transformed_data_list = [
        (1, data_size_config[1][1]["totalsize"] / bytes_per_second),
        (None, 0),
    ]

    lists = []

    for i in range(1, device_count):
        lists.append([(i, val) for val in transformed_data_list])

    lists.append(
        [(device_count, val) for val in transformed_data_list if val[0] != None]
    )

    # Get all permutations of elements across the lists
    perms = list(itertools.product(*lists))

    result_dict = {key[0]: [] for key in transformed_data_list if key[0] != None}

    for permutation in perms:
        for perm_item in permutation:
            if perm_item[0] == 4:
                result_dict[perm_item[1][0]].append(
                    [
                        item[1][1]
                        for item in permutation
                        if item[0] != 4 and item[1][0] != None
                    ]
                )

    result_dict = {
        key: set(
            td(
                seconds=(sum(value_list) if len(value_list) != 0 else 0)
                + data_size_config[key][1]["totalsize"] / bytes_per_second
            )
            for value_list in value_sets
        )
        for key, value_sets in result_dict.items()
    }
    result_dict = {key: sorted(value) for key, value in result_dict.items()}

    return {"comp": computation_time, "comm": result_dict}


def basic_FTP_no_comms(
    data_size_config: Dict,
    processing_time_config: Dict,
    bytes_per_second: float,
    cores_per_device: int,
) -> Dict:
    computation_time: td = td()
    communication_time: td = td()

    conv_blocks = list(data_size_config.keys())

    communication_time = td(
        seconds=data_size_config[1][1]["totalsize"] / bytes_per_second
    )
    for conv_block in conv_blocks:
        partition_config = ftp_fetch_highest_partition_conf_per_block(
            block_data_size_config=data_size_config[conv_block],
            max_core_conf=cores_per_device,
        )

        computation_time = computation_time + td(
            seconds=(
                processing_time_config[conv_block][partition_config]["mean"]
                + processing_time_config[conv_block][partition_config]["stdev"]
            )
        )
    return {"comp": computation_time, "comm": communication_time}


def basic_FTP_comp_vs_comm(
    data_size_config: Dict,
    processing_time_config: Dict,
    bytes_per_second: float,
    device_count: int,
    core_per_device: int,
) -> Dict:

    computation_time: td = td()
    communication_time: td = td()

    conv_blocks = list(data_size_config.keys())
    conv_blocks.append(None)

    list_a = [[conv_blocks[0]]] + (
        [[item for item in conv_blocks]] * (device_count - 1)
    )

    all_combinations = list(product(*list_a))

    max_core_allowance = (device_count * core_per_device) / 2

    # Generate all permutations of the valid combinations
    permutations_set = all_combinations

    comp = td(seconds=0)
    results_dict = {
        str(val): ftp_basic_sim(
            data_size_config=data_size_config,
            processing_time_config=processing_time_config,
            bytes_per_second=bytes_per_second,
            offsets=val,
            max_partition_size=max_core_allowance,
        )
        for val in permutations_set
    }

    sum_proc_times = 0
    for blocks in processing_time_config.keys():
        max_part = ftp_fetch_highest_partition_conf_per_block(
            block_data_size_config=data_size_config[blocks],
            max_core_conf=max_core_allowance,
        )
        sum_proc_times = (
            sum_proc_times
            + processing_time_config[blocks][max_part]["mean"]
            + processing_time_config[blocks][max_part]["stdev"]
        )

    td_proc = td(seconds=sum_proc_times)

    return {"comp": td_proc, "comm": results_dict}


def ftp_basic_sim(
    data_size_config: Dict,
    processing_time_config: Dict,
    bytes_per_second: float,
    offsets: Set,
    max_partition_size: int,
) -> td:

    initial_time = dt.now()
    current_time = dt.now()
    start_times = [None] * 4

    actual_start_times = []
    actual_finish_times = [None] * 4

    network_link = []

    for i in range(len(offsets)):
        if i == 0:
            current_time = initial_time
        else:
            if offsets[i] != None:
                current_time = start_times[i - 1]
        actual_start_times.append(current_time)
        for blocks in data_size_config.keys():
            if i != len(offsets) - 1 and blocks == offsets[i + 1]:
                start_times[i] = current_time

            partition_config = ftp_fetch_highest_partition_conf_per_block(
                block_data_size_config=data_size_config[blocks],
                max_core_conf=max_partition_size,
            )

            upload_list = []

            # Calculate input upload
            for tile_size in data_size_config[blocks][partition_config]["per_tile"]:
                network_link, return_window = find_earliest_link_slot(
                    current_time=current_time,
                    estimated_time_window=td(seconds=tile_size / bytes_per_second),
                    network_link=network_link,
                )
                upload_list.append(
                    return_window[1]
                    + td(
                        seconds=processing_time_config[blocks][partition_config]["mean"]
                        + processing_time_config[blocks][partition_config]["stdev"]
                    )
                )

            largest_time = current_time

            # Calculate input upload
            for k in range(len(data_size_config[blocks][partition_config]["per_tile"])):
                tile_size = data_size_config[blocks][partition_config]["per_tile"][k]
                network_link, return_window = find_earliest_link_slot(
                    current_time=upload_list[k],
                    estimated_time_window=td(seconds=tile_size / bytes_per_second),
                    network_link=network_link,
                )
                upload_list.append(
                    return_window[1]
                    + td(
                        seconds=processing_time_config[blocks][partition_config]["mean"]
                        + processing_time_config[blocks][partition_config]["stdev"]
                    )
                )

                if largest_time < return_window[1]:
                    largest_time = return_window[1]
            current_time = largest_time
            actual_finish_times[i] = largest_time
        continue

    sum_proc_times = 0
    for blocks in processing_time_config.keys():
        max_core_allowance = ftp_fetch_highest_partition_conf_per_block(
            block_data_size_config=data_size_config[blocks],
            max_core_conf=max_partition_size,
        )
        sum_proc_times = (
            sum_proc_times
            + processing_time_config[blocks][max_core_allowance]["mean"]
            + processing_time_config[blocks][max_core_allowance]["stdev"]
        )

    td_proc = td(seconds=sum_proc_times)

    comm_list = [
        (actual_finish_times[i] - actual_start_times[i]) - td_proc
        for i in range(len(actual_finish_times))
    ]

    return comm_list[len(comm_list) - 1]


def ftp_fetch_highest_partition_conf_per_block(
    block_data_size_config: Dict, max_core_conf: int
) -> int:
    max_val = 0
    for key in block_data_size_config.keys():
        if key <= max_core_conf and key > max_val:
            max_val = key
    return max_val
