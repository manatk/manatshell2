import os
import subprocess
import shlex
import glob as Glob
import signal
import copy

#Job class is an extension of the subprocess module. Keeps track of different processes + more information
class Job:
    def __init__(self, process, type):
        self.process = process
        self.pid = process.pid
        self.status = process.poll()
        self.type = type

#remove any processes which are no longer running. My processes list keeps track of only active jobs
def clean_processes(running_processes):
    try:
        for job in running_processes:
            if job.process.poll() != None:
                running_processes.remove(job)
    except:
        print("ERROR WITH CLEANING")

#launch the piping. redirect output and create new subprocesses for the different commands to pipe
def launch_piping(split_commands_to_pipe, processes,input_redirection,output_redirection):
    type = "foreground"
    if "&" in split_commands_to_pipe:
        type = "background"
    first_sbp = subprocess.Popen(split_commands_to_pipe[0], stdout=subprocess.PIPE)
    first_job = Job(first_sbp, type)
    processes.append(first_job)
    parent = first_sbp

    for i in range(1,len(split_commands_to_pipe)-1):
        middle_process = subprocess.Popen(split_commands_to_pipe[i], stdin=parent.stdout, stdout=subprocess.PIPE)
        job = Job(middle_process, type)
        processes.append(job)
        parent = middle_process

    last_subprocess = subprocess.Popen(split_commands_to_pipe[-1], stdin=parent.stdout)
    last_job = Job(last_subprocess, type)

    processes.append(last_job)
    return processes

#I split the different subcommands and then use the existing execute function
#to execute the different subcommands that are in the input. CANNOT HANDLE NESTED SUBCOMMANDS.
def subcommand(command, processes):
    command = command.replace(')', (''))
    command = command.replace('$', (''))
    command_tokens_split = command.split('(')
    for command in command_tokens_split[::-1]:
        execute(command, processes)

#execute built-in commands and launch subprocesses for the non-built-in commands
def execute(command, processes):
    command_tokens = split_line(command)
    command_updated = str(command)
    updated_command_tokens = copy.deepcopy(command_tokens)
    for i in range (0, len(command_tokens)):
        if command_tokens[i].find('?') > -1 or command_tokens[i].find('*') > -1:
            updated_command_tokens.extend(Glob.glob(command_tokens[i]))
            updated_command_tokens.remove(command_tokens[i])
    command_tokens = updated_command_tokens

    input_redirection = None
    output_redirection = None
    piping = False
    subcommands = False
    clean_processes(processes)

    #check if there is piping
    if "|" in command:
        piping = True
        commands_to_pipe = (command.split("|"))
        split_commands_to_pipe = []
        for i in range(0,len(commands_to_pipe)):
            split_commands_to_pipe.append(split_line(commands_to_pipe[i]))
        command_tokens = split_commands_to_pipe
        print(split_commands_to_pipe)

    #check if there is input redirection
    if "<" in command_tokens:
        index_value = command_tokens.index("<")
        filename = command_tokens[index_value+1]
        command = command_tokens[0:index_value]
        try:
            input_redirection = open(filename, "r")

        except:
            print("Error with redirection")

    #check if there is output redirection
    if ">" in command_tokens:
        print(command_tokens)
        index_value = command_tokens.index(">")
        filename = command_tokens[index_value+1]
        command = command_tokens[0:index_value]
        try:
            output_redirection = open(filename, "w")
        except:
            print("Error with redirection")

    #check if there are subcommands
    if ("($") in command:
        subcommand(command, processes)

    elif command_tokens[0] == "pwd":
        try:
            print(os.getcwd())
        except:
            print("Error with the cwd")

    elif command_tokens[0] == "cd":
        try:
            os.chdir(command_tokens[1])
            print(os.getcwd())
        except:
            print("please enter a valid path for where to go")

    elif command_tokens[0] == "bg":
        print("HERE")
        try:
            pid = command_tokens[1]
            for job in processes:
                print(job.pid)
                if job.pid == int(pid):
                    job.process.send_signal(signal.SIGSTOP)
                    print("SENT STOP SIGNAL")
                    job.process.send_signal(signal.SIGCONT)
        except:
            print("please enter valid arguments")

    elif command_tokens[0] == "jobs":
        print(processes)
        for job in processes:
            if job.type == "background":
                print(job.pid)

    elif command_tokens[0] == "fg":
        print("FG")
        try:
            pid = command_tokens[1]
            for job in processes:
                if job.pid == int(pid):
                    #print(job.pid)
                    job.process.send_signal(signal.SIGCONT)
                    #print("SIGNAL SENT")
                    job.process.wait()
                    print("successfully waited")
        except:
            print("please enter valid arguments")

    else:
        if piping == True:
            print("HERE")
            processes = launch_piping(split_commands_to_pipe, processes, input_redirection, output_redirection)

        else:
            type = "foreground"
            print(command_tokens)
            if "&" in command_tokens:
                type = "background"
                index = command_tokens.index("&")
                command_tokens.remove(command_tokens[index])
                print("JOB WILL BE BACKGROUND JOB")
            sbp = subprocess.Popen(command_tokens, stdin=input_redirection, stdout=output_redirection)
            child_job = Job(sbp,type)
            print(child_job.pid)
            processes.append(child_job)
            if type == "foreground":
                sbp.wait()
    return processes

def split_line(command):
    return(shlex.split(command))

def handler(signum, frame):
    print("GETTING HERE")
    print('Signal handler called with signal', signum)
    raise OSError("Couldn't open device!")

def main():
    running_processes = []
    history = open("shell_history", "w")

    #signal.signal(signal.SIGSTOP, handler)

    while True:
        try:
            command = input("$ ")
            history.write(command)
            history.write("\n")
            if command == "exit":
                print("Exiting shell")
                break
            elif command == "help":
                print("Manat's shell. A basic Python shell. Doesn't support nested subcommands")
            else:
                running_processes = execute(command, running_processes)
        except KeyboardInterrupt:
            print("KEYBOARD INTERRUPT")
            for job in running_processes:
                print(job)
                job.process.send_signal(signal.SIGSTOP)
                print("SIGNAL SENT")

if '__main__' == __name__:
    main()
