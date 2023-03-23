from typing import Dict, List
from datetime import timedelta as td
import matplotlib.pyplot as plt
import numpy as np


def plot_main(results_dict: Dict, root_directory: str):

    for model, model_results in results_dict.items():
        for technique_name, technique_data in model_results.items():
            if technique_name == "ftp" or technique_name == "multisplit":
                full_vertical(model_name=model, technique_name=technique_name,
                              data=technique_data, directory=root_directory)
            elif technique_name == "ftp_no_comm" or technique_name == "no_part":
                plot_no_vert(model_name=model, technique_name=technique_name,
                             data=technique_data, directory=root_directory)
            elif technique_name == "single_split" or technique_name == "single_vert_horizontal":
                single_split(model_name=model, technique_name=technique_name,
                             data=technique_data, directory=root_directory)


def single_split(model_name: str, technique_name: str, data: Dict, directory: str):
    comp = data["comp"]

    for conv_num, conv_data in data["comm"].items():
        x_values = np.arange(1, len(conv_data) + 1)
        y_values = [(comp.total_seconds() / (comp.total_seconds() + val.total_seconds())) * 100 for val in conv_data]
        plt.bar(x_values, y_values)
        plot_title = f"{model_name.upper()} {technique_name.capitalize()} Conv {conv_num}"
        file_name = f"{directory}{model_name.upper()}_{technique_name.capitalize()}_conv{conv_num}.png"
        
        plt.title(plot_title)
        plt.savefig(file_name)
        plt.close()

    return


def full_vertical(model_name: str, technique_name: str, data: Dict, directory: str):
    # max_layer_count = fetch_max_layer_count(mod_name=model_name)
    comp = data["comp"]
    def value_set_lamb(x): return [None if item == 'None' else int(
        item)for item in x.strip('(').strip(')').split(',')]

    x_labels = list(data["comm"].keys())
    x_value = np.arange(1, len(x_labels) + 1)
    y_values = [(data["comp"].total_seconds() / (data["comp"].total_seconds() +
                 value.total_seconds())) * 100 for value in list(data["comm"].values())]

    plt.bar(x_value, y_values)
    plt.xticks(x_value, x_labels)

    plot_title = f"{model_name.upper()} {technique_name.capitalize()}"
    file_name = f"{directory}{model_name.upper()}_{technique_name.capitalize()}.png"

    plt.title(plot_title)
    plt.savefig(file_name)
    plt.close()


def plot_no_vert(model_name: str, technique_name: str, data: Dict, directory: str):
    data_x = np.arange(1, len(data["comm"][1]) + 1)
    data_y = [(data["comp"].total_seconds() / (data["comp"].total_seconds() +
               value.total_seconds())) * 100 for value in data["comm"][1]]
    plt.bar(data_x, data_y)
    plot_title = f"{model_name.upper()} {technique_name.capitalize()}"
    file_name = f"{directory}{model_name.upper()}_{technique_name.capitalize()}.png"
    plt.title(plot_title)
    plt.savefig(file_name)
    plt.close()


# def sum_list_load(value_set_data: List, conv_count: int) -> int:
#     reversed_list = reversed(value_set_data)
#     conv_number = conv_count + 1
#     result = 0

#     for item in reversed_list:
#         if item == None:
#             break
#         else:
#             result = result + (conv_number - 1)

#     return result


# def fetch_max_layer_count(mod_name: str) -> int:
#     layer_count = 0
#     if mod_name == "vgg16":
#         layer_count = 5
#     elif mod_name == "yolo":
#         layer_count = 6
#     return layer_count

#     return
