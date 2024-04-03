#!/bin/bash

SUBJECTID=""
SESSION=""
TMP="/tmp"
ZOOM="2"
LINES="1"
CHECKER="0"
NSLICE="3"

max()
{
    local m="$1"
    for n in "$@"
    do
        [ "$n" -gt "$m" ] && m="$n"
    done
    echo "$m"
}


while getopts 'i:m:o:s:k:l:t:b:z:q:ch' OPTION; do
  case "$OPTION" in
    i)
      INVOL=$OPTARG
      echo "In Volume: $INVOL"
      ;;
    m)
      MASK=$OPTARG
      echo "Mask: $MASK"
      ;;
    o)
      OUTIMG=$OPTARG
      echo "Output Image: $OUTIMG"
      ;;
    s)
      NSLICE=$OPTARG
      echo "Number of slices: $NSLICE"
      ;;
    h)
      printf "Script usage: $(basename $0) \n\
      Required: \n\
      [-i in_volume.nii] \t\t: Background Volume / Image \n\
      [-m mask.nii]  \t\t\t: Mask Volume / image for transparent overlay (will be reduced to dichotomous mask)\n\
      [-o output.png] \t\t\t: Output image \n\
      Optional: \n\
      [-s number_of_slices] \t\t: Number of Slices to sample, defaults to 3; Will be used for X Y and Z and equally distributed between the center 60 percent of the image\n\n\
      [-k subject_id]  \t\t\t: Subject ID to be printed into the header of the image. Must be quoted if whitespace/IFS is included. Only works if Imagemagic is installed. Can also be every other string to identify subject. \n\
      [-l session_id]  \t\t\t: Session ID to be printed into the header of the image. Must be quoted if whitespace/IFS is included. Only works if Imagemagic is installed. Can also be every other string to identify subject.  \n\
      [-t tmp_dir]  \t\t\t: Directory where temporary files are stored. Will create and delete a .../tmp/ directory within the specified directory \n\
      [-b line_breaks_per_dimension]  \t: The number of line breaks introduced per Dimension. Final number of rows is number of linebreaks * 3\n\
      [-z zoom_factor]  \t\t: Zoom Factor to increase image size\n\
      [-q synthseg.lut]  \t\t: Color Lookup table\n\
      [-c] \t\t\t\t: use checkerboard mask for overlay\n\
      [-h] \t\t\t\t: Displays this help, does not run afterwards\n" >&2
      exit 1
      ;;
    k)
      SUBJECTID=$OPTARG
      echo "Subject ID is $SUBJECTID"
      ;;
    l)
      SESSION=$OPTARG
      echo "Session is $SESSION"
      ;;
    q)
      LUT=$OPTARG
      echo "Color Lookup table is $LUT"
      ;;
    t)
      TMP="${OPTARG}"
      echo "Temp folder is $TMP"
      ;;
    b)
      LINES="${OPTARG}"
      echo "Lines per dimension is $LINES"
      ;;
    z)
      ZOOM="${OPTARG}"
      echo "Zoom factor is $ZOOM"
      ;;
    c)
      CHECKER="1"
      ;;
    ?)
      printf "Script usage: $(basename $0) \n\
      Required: \n\
      [-i in_volume.nii] \t\t: Background Volume / Image \n\
      [-m mask.nii]  \t\t\t: Mask Volume / image for transparent overlay (will be reduced to dichotomous mask)\n\
      [-o output.png] \t\t\t: Output image \n\
      Optional: \n\
      [-s number_of_slices] \t\t: Number of Slices to sample, defaults to 3; Will be used for X Y and Z and equally distributed between the center 60 percent of the image\n\n\
      [-k subject_id]  \t\t\t: Subject ID to be printed into the header of the image. Must be quoted if whitespace/IFS is included. Only works if Imagemagic is installed. Can also be every other string to identify subject. \n\
      [-l session_id]  \t\t\t: Session ID to be printed into the header of the image. Must be quoted if whitespace/IFS is included. Only works if Imagemagic is installed. Can also be every other string to identify subject.  \n\
      [-t tmp_dir]  \t\t\t: Directory where temporary files are stored. Will create and delete a .../tmp/ directory within the specified directory \n\
      [-b line_breaks_per_dimension]  \t: The number of line breaks introduced per Dimension. Final number of rows is number of linebreaks * 3\n\
      [-z zoom_factor]  \t\t: Zoom Factor to increase image size\n\
      [-q synthseg.lut]  \t\t: Color Lookup table\n\
      [-c] \t\t\t\t: use checkerboard mask for overlay\n\
      [-h] \t\t\t\t: Displays this help, does not run afterwards\n" >&2
      exit 1
      ;;
  esac
done
shift "$(($OPTIND -1))"

RTMP="${TMP}/$(openssl rand -hex 20)"
echo $RTMP


if [ -d "$RTMP" ]; then
  # Take action if $DIR exists. #
  echo "Directory ${RTMP} already exists. Script stopped, because it would be forcefully removed otherwise."
  exit 1
fi
mkdir "$RTMP"


fslmaths "${MASK}" -sub 24 -abs -min 1 -mul "${MASK}" "$RTMP/maskClean.nii.gz"

if [ $CHECKER == 1 ]; then
	overlay 0 1 -c "${INVOL}" -a "$RTMP/maskClean.nii.gz" 1 60 "$RTMP/overlay"	
else
	overlay 0 1 "${INVOL}" -a "$RTMP/maskClean.nii.gz" 1 60 "$RTMP/overlay"	
fi


SX=$(awk "BEGIN {printf int( $(fslval $INVOL dim1) * $(fslval $INVOL pixdim1) )}" | tr "," ".")
SY=$(awk "BEGIN {printf int( $(fslval $INVOL dim2) * $(fslval $INVOL pixdim2) )}" | tr "," ".")
SZ=$(awk "BEGIN {printf int( $(fslval $INVOL dim3) * $(fslval $INVOL pixdim3) )}" | tr "," ".")

MAXXY=$(max $SX $SY)

SXF=$(awk "BEGIN {printf $ZOOM * ($MAXXY / $SX)}" | tr "," ".")
SYF=$(awk "BEGIN {printf $ZOOM * ($MAXXY / $SY)}" | tr "," ".")
#SZF=$(awk "BEGIN {printf $ZOOM * ($MAXXYZ / $SZ)}" | tr "," ".")

echo "Image dimensions/Zoom Factor Correction: $SY / $SX / $SZ /// $SYF / $SXF "


SPL=$(awk -v a="$NSLICE" -v b="$LINES" 'function ceil(x){return int(x)+(x>int(x))} BEGIN {printf "%s", ceil(a/b)}')
echo "Slices Per Line: $SPL"


STEPSIZE=$(awk "BEGIN {printf (0.6/($NSLICE -1))}" | tr "," ".")
echo "Stepsize: $STEPSIZE"
for (( i=1; i<=$NSLICE; i++ ))
do 
	STEP=$(awk "BEGIN {printf 0.2+(0.6/($NSLICE -1)*($i - 1))}" | tr "," ".")
	echo "Slicing: $STEP"
	slicer "$RTMP/overlay.nii.gz" -L -l ${LUT} -s $SYF -x $STEP $RTMP/x${i}.png 
	slicer "$RTMP/overlay.nii.gz" -L -l ${LUT} -s $SXF -y $STEP $RTMP/y${i}.png
	slicer "$RTMP/overlay.nii.gz" -L -l ${LUT} -s $SXF -z $STEP $RTMP/z${i}.png
	
done

echo "Stitching image..."
pngappend $(echo | awk -v s="$NSLICE" -v d="$RTMP" -v p="$SPL" '{for (i=1; i<=s; i++){ printf("%s/x%s\.png ", d, i); if (i%p == 0 && i<s) {printf("- ")} else if (i<s) {printf("+ ")}}; printf("- "); for (i=1; i<=s; i++){ printf("%s/y%s\.png ", d, i); if (i%p == 0 && i<s) {printf("- ")} else if (i<s) {printf("+ ")}}; printf("- "); for (i=1; i<=s; i++){ printf("%s/z%s\.png ", d, i);  if (i%p == 0 && i<s) {printf("- ")} else if (i<s) {printf("+ ")}}}') "${RTMP}/o.png"

#if ! command -v R &> /dev/null
if true
then
    echo "R could not be found. Images missing file and mask name. Install R to use R."
    mv "${RTMP}/o.png" "${OUTIMG}"
else 
	RFILE="${RTMP}/stringToImage.R"
	cat > $RFILE <<- EOM
	library(png)
	img <- readPNG("${RTMP}/o.png")
	width <- dim(img)[2]
	height <- dim(img)[1] * 0.05
	string <- "${SUBJECTID} ${SESSION}\n${INVOL}\n${MASK}"

	textPlot <- function(plotname, string, width, height){
	png(plotname, width = width, height = height, units = "px")
	par(mar=c(0,0,0,0), bg = 'black')
	plot(c(0, 1), c(0, 1), ann = F, bty = 'n', type = 'n', xaxt = 'n', yaxt = 'n')
	text(x = 0, y = 0.5, string, cex = 1.5 * (height/100), col = "white", family = "mono", font=2, adj=c(0,0.5))
	dev.off()
	}
	textPlot("${RTMP}/n.png", string, width, height)

	EOM
	Rscript $RFILE
	pngappend "$RTMP/n.png" - "${RTMP}/o.png" "${OUTIMG}"
fi

rm -rf "$RTMP"

#ar=($x $z $y)
#echo "${ar[*]}" | sort -nr | head -n1
#if (i%p == 0 && i<s) {printf("- ")} else if (i<s) {printf("+ ")}}
#{if ($3/$2 % 10 != 0)

# echo | awk -v x="$NSLICE" '{for (i=1; i<=x; i++){ printf("z%s\.png ", i); if (i<x) {printf("+ ")}}}'

# echo | awk -v s="10" -v d="$PWD" '{for (i=1; i<=s; i++){ printf("%s/tmp/z%s\.png ", d, i); if (i<s) {printf("+ ")}}}'

# echo | awk -v s="1" -v d="$PWD" '{for (i=1; i<=s; i++){ printf("%s/tmp/x%s\.png ", d, i); if (i<s) {printf("+ ")}}; printf("- "); for (i=1; i<=s; i++){ printf("%s/tmp/y%s\.png ", d, i); if (i<s) {printf("+ ")}}; printf(" - "); for (i=1; i<=s; i++){ printf("%s/tmp/z%s\.png ", d, i); if (i<s) {printf("+ ")}}}'

# echo | awk 'function ceil(x, y){y=int(x); return(x>y?y+1:y)} {printf "%s", ceil(5/2)}'
