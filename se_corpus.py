#!/usr/bin/env python3

# Creates a csv file named se_corpus-yyyy-mm-dd.csv in working directory

import csv
import requests
import re
import sys


REPO_BASE_URL = "https://api.github.com/users/standardebooks/repos?per_page=100&page="
RAW_FILE_URL_STEM = "https://raw.github.com/"
PATH_TO_CONTENT_OPF = "/master/src/epub/content.opf"
PATH_TO_COLOPHON = "/master/src/epub/text/colophon.xhtml"

# Strings used as search patterns in content.opf and colophon.xhtml:
FINDS_TITLE = 'meta property="file-as" refines="#title'
FINDS_SE_SUBJECT = 'meta property="se:subject"'
FINDS_DESCRIPTION = 'dc:description id="description"'
FINDS_AUTHOR = 'meta property="file-as" refines="#author"'
FINDS_ARTIST = 'dc:contributor id="artist"'
FINDS_PRODUCER = 'meta property="file-as" refines="#producer-1"'
FINDS_PUB_DATE = "<dc:date>"
FINDS_REV_DATE = 'meta property="dcterms:modified"'
FINDS_PAINTING = 'epub:type="se:name.visual-art.painting"'

# Dictionary keys:
KEY_TITLE = "Title"
KEY_SE_SUBJECT = "SE subject"
KEY_DESCRIPTION = "Description"
KEY_AUTHOR = "Author"
KEY_ARTIST = "Artist"
KEY_PRODUCER = "Producer"
KEY_PUB_DATE = "Pub date"
KEY_REV_DATE = "Rev date"
KEY_PAINTING = "Painting"

# Launch flags and args:
FLAG_VERBOSE = False
FLAG_VERY_VERBOSE = False
FLAG_QUIET = False
ARG_FILEPATH = ""


# Firing order: functions fire in this order:
# parse_args()
# save_csv_to_path
# 	complete_corpus_list()
#		get_repo_urls()
#		dict_from_repo_url()
#			content_opf_from_repo_url()
#			dict_from_content_opf_string()
#				strip_and_remove_tags()
#				reformat_time_string()
#		colophon_from_repo_url()
#		painting_from_colophon_string()

# 	write_csv_from_list_to_path()


# Returns a list of repo urls
def get_repo_urls():
	output_info_for_type("Looking for repos...", "", False)
	page = 0
	rv = []
	last_page = False
	while last_page == False:
		page += 1
		full_url = REPO_BASE_URL + str(page)
		output_info_for_type("Checking " + full_url, "v", False)
		obj = requests.get(full_url)
		text = obj.text
		if len(text) < 100:
			last_page = True
		else:
			lines = text.split(",")
			for line in lines:
				if '"full_name":' in line:
					# line looks like: "full_name":"standardebooks/a-a-milne_the-red-house-mystery"
					full_name = line[13:-1]
					repo_url = RAW_FILE_URL_STEM + full_name
					rv.append(repo_url)
					output_info_for_type("Found repo at " + repo_url, "vv", False)
	output_info_for_type("Repos found: " + str(len(rv)), "v", False)	
	return rv


# Return text of content.opf page
def content_opf_from_repo_url(repo_url):
	rv = ""
	content_opf_url = repo_url + PATH_TO_CONTENT_OPF
	content_opf_resp = requests.get(content_opf_url)
	if content_opf_resp.ok == True:
		rv = content_opf_resp.text
		output_info_for_type("Found content.opf for " + repo_url, "vv", False)
	else:
		output_info_for_type("No content.opf found for " + repo_url, "", False)
	return rv


# Returns text of colophon.xhtml
def colophon_from_repo_url(repo_url):
	rv = ""
	colophon_url = repo_url + PATH_TO_COLOPHON
	colophon_resp = requests.get(colophon_url)
	if colophon_resp.ok == True:
		rv = colophon_resp.text
		output_info_for_type("Found colophon.xhtml for " + repo_url, "vv", False)
	else:
		output_info_for_type("No colophon.xhtml found for " + repo_url, "", False)
	return rv


# Returns a dict that has all data except name of painting
def dict_from_repo_url(repo_url):
	content_opf_string = content_opf_from_repo_url(repo_url)
	rv = dict_from_content_opf_string(content_opf_string)
	return rv


def strip_and_remove_tags(s):
	s = s.strip()
	return re.sub('<[^<]+?>', '', s)


def reformat_time_string(time_string):
	# Times comes in like this: 2021-05-12T22:13:51Z
	return time_string[:10]


def dict_from_content_opf_string(s):
	rv = {KEY_TITLE:'', KEY_SE_SUBJECT:'', KEY_DESCRIPTION:'', KEY_AUTHOR:'', KEY_ARTIST:'', KEY_PRODUCER:'', KEY_PUB_DATE:'', KEY_REV_DATE:''}
	
	lines = s.split("\n")
	for line in lines:
		if FINDS_TITLE in line:
			rv[KEY_TITLE] = strip_and_remove_tags(line)
		elif FINDS_SE_SUBJECT in line:
			rv[KEY_SE_SUBJECT] = strip_and_remove_tags(line)
		elif FINDS_DESCRIPTION in line:
			rv[KEY_DESCRIPTION] = strip_and_remove_tags(line)
		elif FINDS_AUTHOR in line:
			rv[KEY_AUTHOR] = strip_and_remove_tags(line)
		elif FINDS_ARTIST in line:
			rv[KEY_ARTIST] = strip_and_remove_tags(line)
		elif FINDS_PRODUCER in line:
			rv[KEY_PRODUCER] = strip_and_remove_tags(line)
		elif FINDS_PUB_DATE in line:
			pub_date = strip_and_remove_tags(line)
			rv[KEY_PUB_DATE] = reformat_time_string(pub_date)
		elif FINDS_REV_DATE in line:
			rev_date = strip_and_remove_tags(line)
			rv[KEY_REV_DATE] = reformat_time_string(rev_date)
	return rv


def painting_from_colophon_string(s):
	rv = ""
	lines = s.split("\n")
	for line in lines:
		if FINDS_PAINTING in line:
			rv = strip_and_remove_tags(line)
			# Remove trailing period:
			rv = rv[:-1]
			output_info_for_type("Found painting in colophon.xhtml", "vv", False)
			break
	if rv == "":
		output_info_for_type("No painting found in colophon", "v", False)
	return rv


def complete_corpus_list():
	rv = []
	repo_urls = get_repo_urls()
	for repo_url in repo_urls:
		# Create a dict for data from content.opf:
		repo_dict = dict_from_repo_url(repo_url)
		# Add painting name from colophon:
		colophon = colophon_from_repo_url(repo_url)
		painting = painting_from_colophon_string(colophon)
		repo_dict[KEY_PAINTING] = painting
		rv.append(repo_dict)
		output_info_for_type("Got metadata for " + repo_url, "vv", False)
	return rv


def write_csv_from_list_to_path(corpus_list, filepath):
	# This array sets the column order:
	field_names = [KEY_TITLE, KEY_AUTHOR, KEY_SE_SUBJECT, KEY_ARTIST, KEY_PAINTING, KEY_PRODUCER, KEY_PUB_DATE, KEY_REV_DATE, KEY_DESCRIPTION]
	
	# To get a header on the first line of the csv, prepend a dict where key and value are the same.
	header_dict = {}
	for field_name in field_names:
		header_dict[field_name] = field_name
	corpus_list.insert(0, header_dict)
	
	output_info_for_type("Writing csv file.", "vv", True)
	with open(filepath, 'w') as csv_file:
		dict_object = csv.DictWriter(csv_file, fieldnames = field_names) 
		for dict in corpus_list:
			dict_object.writerow(dict)
			output_info_for_type(".", "vv", True)
	output_info_for_type("", "vv", False)


def save_csv_to_path(filepath):
	corpus_list = complete_corpus_list()
	write_csv_from_list_to_path(corpus_list, filepath)

	
def print_usage():
	print("Usage: python3 se_corpus.py filepath")
	print("Optional flags: -v (verbose); -vv (very verbose); -q (quiet); -h or --help: usage")
	sys.exit()


def output_info_for_type(s, verbosity, suppress_newline):
	# verbosity is "", "v", or "vv"; suppress_newline is True or False
	global FLAG_QUIET
	global FLAG_VERBOSE
	global FLAG_VERY_VERBOSE
	if FLAG_QUIET == True:
		return
	if verbosity == "vv":
		if FLAG_VERY_VERBOSE == True:
			if suppress_newline == True:
				print(s, end='')
			else:
				print(s)
	elif verbosity == "v":
		if FLAG_VERBOSE == True:
			if suppress_newline == True:
				print(s, end='')
			else:
				print(s)
	else:
		if suppress_newline == True:
			print(s, end='')
		else:
			print(s)


def parse_args():
	args = sys.argv
	args_count = len(args)
	global ARG_FILEPATH
	global FLAG_QUIET
	global FLAG_VERBOSE
	global FLAG_VERY_VERBOSE
	for n in range(1, args_count):
		arg = args[n]
		print(arg)
		if arg == "--help":
			print_usage()
		elif arg.startswith("-"):
			if "vv" in arg:
				FLAG_VERY_VERBOSE = True
			elif "v" in arg:
				FLAG_VERBOSE = True
			elif "q" in arg:
				FLAG_QUIET = True
			elif "h" in arg:
				print_usage()
		else:
			ARG_FILEPATH = arg
	if len(ARG_FILEPATH) < 1:
		print_usage()


	

###########################

if __name__ == "__main__":
	parse_args()
	save_csv_to_path(ARG_FILEPATH)
