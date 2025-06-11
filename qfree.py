#!/usr/bin/python3
import argparse
import subprocess
import sys
import xml.etree.ElementTree as ET

# ----------------------------------------------

col_widths = [14, 10, 12]
def nice_format(values):
  result = ""
  for i, val in enumerate(values):
    val = str(val)
    val_clean = val
    for s in ansi_colors.values():
      val_clean = val_clean.replace(s, "")
    spaces = " " * max(col_widths[i] - len(val_clean), 0)
    result += val + spaces
  return result

ansi_colors = {"red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
  "black": "\033[90m", "bold": "\033[1m", "clear": "\033[0m"}
def colored(text, color):
  if args.nocolor or color not in ansi_colors:
    return text
  else:
    return "{}{}\033[0m".format(ansi_colors[color], text)

# ----------------------------------------------

parser = argparse.ArgumentParser(
  prog="qfree",
  description="Lists how many processors (CPU threads) are available for each node in the cluster.",
  epilog=\
"""Meaning of the state column:
  free: all processors are available
  avail: some processors are available, but not all
  full: no processors available on this node
  offline: node not accepting jobs
  down: node is down

Author: Juan C. Toledo
This program is free software made available under the GPLv3 license.
Bug reports and suggestions welcome!
""",
  formatter_class=argparse.RawTextHelpFormatter
)
parser.add_argument("-a", "--all", action="store_true", help="Show all nodes, including offline / down.")
parser.add_argument("-j", "--jobs", dest="job_id", const="all", nargs="?", help="Show processor counts for all jobs, or a specific JOB_ID if given")
parser.add_argument("-n", "--nocolor", action="store_true", help="Don't use colored output")
args = parser.parse_args()

# ----------------------------------------------

stdout = subprocess.check_output("pbsnodes -x", shell=True).strip().decode("ascii")
root = ET.fromstring(stdout)

# ----------------------------------------------

print(colored(nice_format(["Node", "State", "Procs avail / total"]), "bold"))

tot_counts = {"avail": [], "used": []}
for node in root:
  
  name = node.find("name").text.replace(".nucleares.unam.mx", "")
  state_raw = node.find("state").text
  jobs = node.find("jobs")
  np_tot = int(node.find("np").text)
 
  # Count available processes
  np_used = 0
  np_avail = np_tot
  if jobs is None:
    jobs = {}
  else:
    jobs_cpus = jobs.text.split(", ")
    jobs = {}
    for job_cpu in jobs_cpus:
      cpu, job = job_cpu.split("/")
      cpu = int(cpu)
      job = job.replace(".diable.nucleares.unam.mx", "")
      if job not in jobs: jobs[job] = []
      jobs[job].append(cpu)
    for job,cpu_list in jobs.items():
      np_used += len(cpu_list) 
    np_avail = np_tot - np_used
  
  # Determine and print state
  if state_raw in ["down", "offline"]:
    state = state_raw
    if args.all:
      print(nice_format([name, colored(state_raw, "black"), ""]))
  elif state_raw in ["free", "job-exclusive"]:
    if np_used == 0:
      state = "free"
      color = "green"
    elif np_used < np_tot:
      state = "avail"
      color = "yellow"
    elif np_used == np_tot:
      state = "full"
      color = "red"
    state_str = colored(state, color)
    procs_str = "{} / {}".format(colored(np_avail, color), np_tot)
    print(nice_format([name, state_str, procs_str]))
  else:
    state = state_raw
    print(nice_format([name, state, np]))

  if state not in ["down", "offline"]:
    if np_avail > 0:
      tot_counts["avail"].append(np_avail)
    if np_used > 0:
      tot_counts["used"].append(np_used)

  # Print jobs on this node
  if args.job_id is not None:
    for job_id, cpu_list in jobs.items():
      if args.job_id == "all" or args.job_id == job_id:  
          print("  Job {}: {} procs in use".format(job_id, colored(len(cpu_list), "bold")))

if args.job_id not in ["all", None]:
  print("(Showing job {} only)".format(colored(args.job_id, "bold")))

# Show totals
tot_avail = sum(tot_counts["avail"])
tot_inuse = sum(tot_counts["used"])
tot_procs = tot_avail + tot_inuse
print("Procs: {} free, {} in use, {} total".format(colored(tot_avail, "green"), colored(tot_inuse, "red"), tot_procs))
