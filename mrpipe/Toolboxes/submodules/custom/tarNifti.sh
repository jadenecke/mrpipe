#!/bin/bash
SHOW=false
REMOVE=false
FORCE=""
NPROC=1
while getopts 'd:n:shrf' OPTION; do
  case "$OPTION" in
    d)
      TDIR=$OPTARG
      echo "Target directory: $TDIR"
      ;;
    n)
      NPROC=$OPTARG
      echo "Number of threads used: $NPROC"
      ;;
    s)
      SHOW=true
      echo "Only showing files, not compressing"
      ;;
    r)
      REMOVE=true
      echo "Removing .nii files if .nii.gz already exists"
      ;;
    f)
      FORCE=" -f "
      echo "Force overwrite existing files"
      ;;
    h)
      printf "Script usage: $(basename $0) \n\n\
      Required: \n\
      [-d path/to/dir] \t\t: directory with .nii files. Searches recursively. May contain wildcards if path is quoted \n\\n\
      
      Optional:\n\
      [-s] \t\t\t: Only show files which would be compressed. \n\
      [-n] \t\t\t: Number of threads used. Defaults to 1. \n\
      [-r] \t\t\t: Remove .nii files if .nii.gz already exists. Overrules -f if .nii.gz file exists \n\
      [-f] \t\t\t: force overwrite of output file and compress links. \n\
      [-h] \t\t\t: Displays this help, does not run afterwards\n" >&2
      exit 1
      ;;
    ?)
      printf "Script usage: $(basename $0) \n\n\
      Required: \n\
      [-d path/to/dir] \t\t: directory with .nii files. Searches recursively / Image \n\\n\
      
      Optional:\n\
      [-s] \t\t\t: Only show files which would be compressed. \n\
      [-n] \t\t\t: Number of threads used. Defaults to 1. \n\
      [-r] \t\t\t: Remove .nii files if .nii.gz already exists. Overrules -f  \n\
      [-f] \t\t\t: force overwrite of output file and compress links. \n\
      [-h] \t\t\t: Displays this help, does not run afterwards\n" >&2
      exit 1
      ;;
  esac
done
shift "$(($OPTIND -1))"


if [ -z "$TDIR" ]; then echo "ERROR: target directory (-d) is not set or blank"; exit 1; fi


if $SHOW; then
	find $TDIR -name "*.nii"
	exit 0
fi

if $remove; then
	find $TDIR -name "*.nii" -print0 | xargs -0 -P $NPROC -I % sh -c "echo %; if [ -f %.gz ]; then rm -v %; else gzip $FORCE %; fi"
else
	find $TDIR -name "*.nii" -print0 | xargs -0 -P $NPROC -I % sh -c "echo %; gzip $FORCE %"
fi