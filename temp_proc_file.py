import json
from datetime import timedelta
import pickle

def load_pickle(file_path):
    with open(file_path, 'rb') as f:
        data = pickle.load(f)
    return data
    
vgg16_data = load_pickle("./VGG16.pkl")
yolo_data = load_pickle("./YOLO.pkl")
mobile_net_data = load_pickle("./MOBILENETV2.pkl")
yolo_single_split = yolo_data["single_split"]
avg = sum(yolo_single_split[4]) / len(yolo_single_split[4])
print()