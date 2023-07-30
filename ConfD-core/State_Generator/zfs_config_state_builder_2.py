#!/usr/bin/python3

import cmd
import json
import copy
import math
import sys, getopt
import random
import pdb
import os

from setuptools import Command

depth = 0
states_made = 0

max_depth = 0

argument_key = {
    "blocksize": "-b", "feature": "-o"
}

reverse_argument_key = {v: k for k, v in argument_key.items()}

feature_args = {
        "volblocksize", "checksum", "compression", "copies"
        }

default_feature_args = {
        "volblocksize": 8192,
        "checksum": 0,
        "compression": 0,
        "copies": 2
        }


class Configuration:
    arg = None
    
    def __init__(self):
        self.arg = dict()
        for a in default_feature_args:
            self.arg[a] = default_feature_args[a]

#finds next largest number power of 2
#https://www.techiedelight.com/round-next-highest-power-2/
def nextPow2(n):
    # decrement `n` (to handle cases when `n` itself
    # is a power of 2)
    n = n - 1
    
    # do till only one bit is left
    while n & n - 1:
        n = n & n - 1       # unset rightmost bit
    
    #'n' is now a power of two

    #return next power of two
    return n << 1

#looks up by id for constraint_data
def id_lookup(constraint_data, id):
    for i in constraint_data:
        if(constraint_data[i]['id'] == id):
            return(i)
    

#Takes command line style config, adds params to existing Configuration
def read_config(line, my_config):
    params = line.split(' -')
    #Parse command parameter
    for param in params:
        if(param != "(mkezfs)" and param != "\n" and param[0] != 'O'):
                    
            #print(param.strip().split(' '))
            key=param.strip().split(' ')[0]
            val=param.strip().split(' ')[1]
            my_config.arg[reverse_argument_key["-"+key]]=val
                    
            #print(reverse_argument_key["-"+key])
        
        #case '-O'
        elif (param[0] == 'O'):
            clean = param.strip().split(' ')[1].split(',')
            for c in clean:
                my_config.arg[c] = ""
            

#Determines if a given Configuration is valid within given constraints
def verify_config(my_config, constraint_data):
    #Step 1 - verify all numerical constraints
    #TODO account for postfixs on numbers
    for a in my_config.arg:
        if(a != "revision" and a != "encoding"):
            #print(constraint_data[a])
            #print(a + " : " + my_config.arg[a])
            if(constraint_data[a]["takes_value"] == "yes"):
                #Tests Max
                if(constraint_data[a]["value_range_max"] != None and (int(constraint_data[a]["value_range_max"]) < int(my_config.arg[a]))):
                    #print("Max:" + constraint_data[a]["value_range_max"])
                    #print("Act:" + my_config.arg[a])
                    #print(constraint_data[a])
                    #print(" Max violated")
                    return False
                #Tests Min
                if(constraint_data[a]["value_range_min"] != None and (int(constraint_data[a]["value_range_min"]) > int(my_config.arg[a]))):
                    #print(constraint_data[a])
                    #print(" Min violated")
                    return False


    #Step 2 - verify critical enabled/disabled and smaller
    for a in my_config.arg:
        if(a != "revision" and a != "encoding"):
            #print(constraint_data[a])
            #print(a + " : " + my_config.arg[a])
            if(constraint_data[a].get("critical", None) != None):
                #print(constraint_data[a]["critical"])
                for crit in constraint_data[a]["critical"]:
                    #print(crit + " : " + constraint_data[a]["critical"][crit])
                    #enabled crit test
                    if((constraint_data[a]["critical"][crit] == "enable") and ((my_config.arg.get(crit, None) == None) or (my_config.arg[crit] == "disable"))):
                        #print(constraint_data[a])
                        #print(crit + " violated")
                        #print("")
                        return False
                    if((constraint_data[a]["critical"][crit] == "disable") and (my_config.arg.get(crit, None) != None) and (my_config.arg[crit] == "enable")):
                        #print(constraint_data[a])
                        #print(crit + " violated")
                        #print("")
                        return False
                    #tests smaller
                    if((constraint_data[a]["critical"][crit] == "smaller") and (my_config.arg.get(crit, None) != None)):
                        if(int(my_config.arg[a]) < int(my_config.arg[crit])):
                            #print(constraint_data[a])
                            #print(crit + " violated")
                            #print("")
                            return False
    return True

#Generates states up to target number
def generate(my_config, constraint_data, target_num, final_states, try_list):
    global states_made
    global depth
    depth += 1
    for id in try_list:
        #checks if valid id num
        if(id_lookup(constraint_data, id) != None):
            print("looking at " + id_lookup(constraint_data, id))
            #check if completed task
            if(states_made >= target_num):
                depth -= 1
                return

            #checks if too deep
            if(depth > max_depth):
                depth -= 1
                return

            #creates new state(s)
            new_configs = []
            temp = copy.deepcopy(my_config)
            new_configs.append(temp)

            #checks if arg already present
            if(my_config.arg.get(id_lookup(constraint_data, id), None) != None):
                if(default_feature_args.get(id_lookup(constraint_data, id), None) == None):
                    #case not defualt but dup
                    continue
                else:
                    #case default
                    if(constraint_data[id_lookup(constraint_data, id)]["takes_value"] == "no"):
                        #case no parameter
                        temp.arg[id_lookup(constraint_data, id)]="disable"
                    elif(constraint_data[id_lookup(constraint_data, id)]["value_range_min"] != None):
                        if(constraint_data[id_lookup(constraint_data, id)]["value_range_max"] != None):
                            #case min and max
                            temp2 = copy.deepcopy(my_config)
                            new_configs.append(temp2)
                            temp3 = copy.deepcopy(my_config)
                            new_configs.append(temp3)

                            temp.arg[id_lookup(constraint_data, id)]=constraint_data[id_lookup(constraint_data, id)]["value_range_min"]
                            temp2.arg[id_lookup(constraint_data, id)]=constraint_data[id_lookup(constraint_data, id)]["value_range_max"]
                            temp3.arg[id_lookup(constraint_data, id)]=nextPow2(int(constraint_data[id_lookup(constraint_data, id)]["value_range_min"]) + 1)
                        else:
                            #case just min
                            temp.arg[id_lookup(constraint_data, id)]=constraint_data[id_lookup(constraint_data, id)]["value_range_min"]
                    else:
                        #case just max
                        temp.arg[id_lookup(constraint_data, id)]=1

            else:
                #case not a dup
                if(constraint_data[id_lookup(constraint_data, id)]["takes_value"] == "no"):
                    #case no parameter
                    temp.arg[id_lookup(constraint_data, id)]="enable"
                elif(constraint_data[id_lookup(constraint_data, id)]["value_range_min"] != None):
                    if(constraint_data[id_lookup(constraint_data, id)]["value_range_max"] != None):
                        #case min and max
                        temp2 = copy.deepcopy(my_config)
                        new_configs.append(temp2)
                        temp3 = copy.deepcopy(my_config)
                        new_configs.append(temp3)

                        temp.arg[id_lookup(constraint_data, id)]=constraint_data[id_lookup(constraint_data, id)]["value_range_min"]
                        temp2.arg[id_lookup(constraint_data, id)]=constraint_data[id_lookup(constraint_data, id)]["value_range_max"]
                        temp3.arg[id_lookup(constraint_data, id)]=nextPow2(int(constraint_data[id_lookup(constraint_data, id)]["value_range_min"]) + 1)
                    else:
                        #case just min
                        temp.arg[id_lookup(constraint_data, id)]=constraint_data[id_lookup(constraint_data, id)]["value_range_min"]
                else:
                    if(constraint_data[id_lookup(constraint_data, id)]["value_range_max"] != None):
                        #case just max
                        temp2 = copy.deepcopy(my_config)
                        new_configs.append(temp2)

                        temp.arg[id_lookup(constraint_data, id)]=constraint_data[id_lookup(constraint_data, id)]["value_range_max"]
                        temp2.arg[id_lookup(constraint_data, id)]=1
                    else:
                        #case no min/max
                        temp.arg[id_lookup(constraint_data, id)]=1


            for temp_config in new_configs:
                #print(temp_config.arg)
                #checks if state already been added
                seen = False
                for past in final_states:
                    if(past.arg == temp_config.arg):                #TODO write comparator?
                        seen = True
                if(seen == False):
                    #adds configuration if deep enough & valid
                    if(depth > 0 and verify_config(temp_config, constraint_data) == True):
                        states_made += 1
                        print("depth: " + str(depth) + "; states made: " + str(states_made))
                        print(temp_config.arg)
                        print(id_lookup(constraint_data, id))
                        print("")
                        final_states.append(temp_config)

                    #determine what to try next
                    next_list = []
                    for name in constraint_data[id_lookup(constraint_data, id)]["dependency"]:
                        next_list.append(constraint_data[name]["id"])
                    if(constraint_data[id_lookup(constraint_data, id)].get("critical", None) != None):
                        for name in constraint_data[id_lookup(constraint_data, id)]["critical"].keys():
                            next_list.append(constraint_data[name]["id"])
                    #print(next_list)
                    #print("")

                    #go deeper
                    generate(temp_config, constraint_data, target_num, final_states, next_list)

    depth -= 1

def getCritDisable(constraint_data):
    global disable
    disable = []
    for a in constraint_data:
        for crit in constraint_data[a]["critical"]:
            if(constraint_data[a]["critical"][crit] == "disable"):
                disable.append(crit)



#attempt to generate the correct number of states with a different algorithm
def simpleGenerate(my_config, constraint_data, target_num, final_states, try_list):
    global states_created
    global state_depth




    return

#converts fron Configuration to command line style 
def ConfigToCMD(config, constraint_data):
    output="zfs create"
    features = []

    for arg in config.arg:
        #Skips if part of default config
        if((default_feature_args.get(arg, None) == None) or ((default_feature_args.get(arg, None) != None) and (str(default_feature_args[arg]) != str(config.arg[arg])))):
            flag = constraint_data[arg]["flag"]
            if(flag == "-o"):
                features.append(arg)
            else:
                output += " " + flag + " " + str(config.arg[arg])

    for item in features:
        output += " -o "
        output += str(item)
        output += "="
        #for these arguments, output on and off rather than 0 or 1
        if (str(item) == "checksum" or str(item) == "compression"):
            if (config.arg[item] == 0):
                output += "on"
            else:
                output += "off"
        else:
            output += str(config.arg[item])

    return output


def main(argv):
    global default_feature_args
    global max_depth
    
    if(not os.path.exists("zfs_constraints.json")):
        print("Missing zfs_constraints.json file")
        return -1

    #if(not os.path.exists("zfs_default_config.json")):
    #    print("Missing zfs_default_config.json file")
    #    return -1

    if(len(sys.argv) != 3):
        print("Invalid arguments")
        return -1
        
    max_depth = int(sys.argv[1])
    max_final_states = int(sys.argv[2])
    
    #get constraints 
    json_file=open('zfs_constraints.json')
    constraint_data = json.load(json_file)
    json_file.close()
    
    #id_lookup(constraint_data, 1)
    #print(constraint_data['blocksize'])
    
    
    #get default configuration
    #json_file=open('zfs_default_config.json')
    #default_feature_args = json.load(json_file)
    #json_file.close()
    
    #Checking some states
    """
    config_file='config_state_ext4.txt'
    with open(config_file, "r", encoding='utf-8') as f:
        Lines = f.readlines()
        
        #Looking at 1 configuration
        for line in Lines:
            
            #Build default config
            my_config = Configuration()
            
            print()
            print(line.strip())
            
            #Modify config based on command line params
            read_config(line, my_config)
            print(my_config.arg)
            
            
            #Verify config
            print(verify_config(my_config, constraint_data))
    """
    my_config = Configuration()
    final_states = []
    generate(copy.deepcopy(my_config), constraint_data, max_final_states, final_states, list(range(1,6)))


    print("Final States")
    output_file = open("zfs_output_2.txt", "w")
    for state in final_states:
        #print(state.arg)
        print(ConfigToCMD(state, constraint_data))
        output_file.write(ConfigToCMD(state, constraint_data) + "\n")
    output_file.close()

    getCritDisable(constraint_data)
    for a in disable:
        print(a)

if __name__ == "__main__":
    main(sys.argv[1:])

