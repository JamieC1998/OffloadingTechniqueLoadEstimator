import data_calc
import plot_results

import json
from typing import Dict
import os


def main():
    root_directory = "./graphs/"

    if os.path.exists(root_directory):
        file_names = os.listdir(root_directory)

        for name in file_names:
            os.remove(f"{root_directory}{name}")
    else:
        os.mkdir(root_directory)

    results_dict = data_calc.data_main()

    plot_results.plot_main(results_dict=results_dict,
                           root_directory=root_directory)
    display_dict = format_results(results_dict=results_dict)

   

    res = json.dumps(display_dict)
    output_file = open("./result_file.json", "w")
    output_file.write(res)
    output_file.close()


def format_results(results_dict: Dict):
    display_dict = {model_name: {technique: {"comp": None, "comm": None}
                                 for technique in results_dict[model_name].keys()} for model_name in results_dict.keys()}

    for model_name, technique_details in results_dict.items():
        for technique_name, technique_results in technique_details.items():
            res = {"comp": None, "comm": None}
            if technique_name == "ftp" or technique_name == "multisplit":
                comp = technique_results["comp"]
                comm = technique_results["comm"]

                for key, val in technique_results["comm"].items():
                    comm[key] = str(val)
                res["comp"] = comp
                res["comm"] = comm
            elif technique_name == "ftp_no_comm" or "no_part":
                comp = technique_results["comp"]
                comm = technique_results["comm"][1]

                for i in range(len(comm)):
                    comm[i] = str(technique_results["comm"][1][i])
                res["comp"] = comp
                res["comm"] = comm
            elif technique_name == "single_split" or technique_name == "single_vert_horizontal":
                comp = technique_results["comp"]
                comm = technique_results["comm"]

                for block in comm.keys():
                    for i in range(len(comm[block])):
                        comm[block][i] = str(
                            technique_results["comm"][block][i])

                res["comp"] = comp
                res["comm"] = comm
            res["comp"] = str(res["comp"])
            display_dict[model_name][technique_name] = res

    return display_dict


if __name__ == "__main__":
    main()
