import pickle
import matplotlib.pyplot as plt

def plot_results(result_file):
    results = pickle.load(open(result_file, 'rb'))
    boxplot_methods = ['ftp', 'multisplit', 'single_split', 'single_vert_horizontal']
    offsets = [0, 0.15*3, 0.15*4, 0.15*5]
    hatches = ['////', '\\\\\\\\', '++', 'xx']
    for load in [1,2,3,4]:
        if load%2:
            plt.fill([load-0.1, load+0.9, load+0.9, load-0.1], [0,0,100,100], color=(0.9,0.9,0.9))
        box = plt.boxplot([results[method][load] for method in boxplot_methods],
                positions=[load+offsets[i] for i in range(0,4)], widths=0.15, patch_artist=True,sym='')
        for patch, hatch in zip(box['boxes'], hatches):
            patch.set_hatch(hatch)
            patch.set_fill(False)
    ftp_no_comm = plt.plot([i+0.15 for i in [1,2,3,4]], [results['ftp_no_comm'][load] for load in [1,2,3,4]], marker='*', linestyle='')
    nopart = plt.plot([i+0.15*2 for i in [1,2,3,4]], [results['no_part'][load] for load in [1,2,3,4]], marker='o', linestyle='')
    plt.xticks([1.5,2.5,3.5,4.5], [1,2,3,4])
    plt.ylim([0,100])
    plt.xlim([0.9, 4.9])
    plt.legend(box['boxes']+[ftp_no_comm[0], nopart[0]],
                ['FTP', 'Multisplit', 'Split', 'Split & Horiz', 'Horiz only', 'No part'],
                ncol=3, bbox_to_anchor=(1,1.15))
    plt.xlabel('Task load')
    plt.ylabel('Computation as percentage of total end to end latency')
    plt.tight_layout()
