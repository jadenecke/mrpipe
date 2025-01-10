#!/usr/bin/env Rscript
library("optparse")
library("RNifti")
require(tictoc, quietly = TRUE)

option_list = list(
  make_option(c("-i", "--in_file"), type="character", default=NA, 
              help="Image file name", metavar="image.nii.gz"),
  make_option(c("-a", "--atlas"), type="character", default=NA, 
              help="Atlas file name", metavar="atlas.nii.gz"),
  make_option(c("-f", "--func"), type="character", default="mean", 
              help="Function to summarize regional values, defaults to mean", metavar="mean"),
  make_option(c("-o", "--out"), type="character", default=NA, 
              help="output file name", metavar="values.csv"),
  make_option(c("-d", "--dots"), type="character", default=NA, 
              help="additional parameter passed to the function call, seperated by spaces and quoted: arg1=val1 arg2=val2", metavar="..."),
  make_option(c("-z", "--keepZeroes"), type="logical", default=FALSE, action="store_true",
              help="Whether to keep zeroes values (usually background) within roi before applying `func`", metavar="FALSE"),
  make_option(c("-n", "--NAtoZero"), type="logical", default=FALSE, action="store_true",
              help="Whether to replace NA values (usually background) with zeroes. Will affect `func` calculation if `--keepZeroes` is also specified.", metavar="FALSE"),            
  make_option(c("-m", "--mask"), type="character", default=NA, 
              help="Mask that is applied to atlas beforehand, e.g. if images were masked themselfs.", metavar="...")
)

opt_parser = OptionParser(option_list=option_list, description = "This function extracts the values of an image for each ROI specified in the atlas. The values are summeraized with the given function call (default = mean), and written to a csv file. Additional dots/eclpis arguments can be specified and the values even be functions themselfs.")
opt = parse_args(opt_parser)

# check date is provided
if (is.na(opt$in_file)) {
  stop("Input file name must be provided. See script usage (--help)")
}
if (is.na(opt$atlas)) {
  stop("Atlas File must be provided. See script usage (--help)")
}
if (is.na(opt$out)) {
  stop("Output file name must be provided. See script usage (--help)")
}

if(!file.exists(opt$in_file)){
  stop(paste0("Input file \"",opt$file, "\" does not exist"))
}
if(!file.exists(opt$atlas)){
  stop(paste0("Atlas file \"", opt$atlas, "\" does not exist"))
}

cat("\nReading Images:" )
Atlas <- readNifti(opt$atlas)
image <- readNifti(opt$in_file)

if(!all(dim(Atlas) == dim(image))){
  stop(paste0("Image file \"", opt$in_file, "\" and Atlas file \"", opt$atlas, "\" do not have the same dimensions"))
}

if(!is.na(opt$mask)){
  mask <- readNifti(opt$mask)
  if(!all(dim(Atlas) == dim(mask))){
    stop(paste0("Mask file \"", opt$mask, "\" and Atlas file \"", opt$atlas, "\" do not have the same dimensions"))
  }
  if(!all(mask %in% c(0,1))){
    stop(paste0("Mask  \"", opt$mask, "\" seems to contain other values than 0 or 1." ))
  }
  cat("\nApplying Mask to Atlas...")
  Atlas[mask == 0] <- 0
}

#arugments processing:
if (!is.na(opt$dots)){
  argsVec <- strsplit(opt$dots, " ")[[1]]
  argName <- lapply(argsVec, function(s){strsplit(s, "=")[[1]][1]})
  argVal <- lapply(argsVec, function(s){strsplit(s, "=")[[1]][2]})
  names(argVal) <- argName
  argList <- argVal
  
  argList <- lapply(argList, type.convert, as.is = TRUE)
  
  cat("\nArgument list: ")
  print(argList)
} else {
  argList <- NULL
}


cat("\nReformatting images...")
ROIs <- unique(as.vector(Atlas))
ROIs <- ROIs[which(ROIs!=0)]
ROIs <- sort(ROIs)
cat(paste0("\nNumber of ROIs in Atlas: ", length(ROIs)))

if(opt$NAtoZero){
  cat(paste0("\nConverting NAs to Zeroes... "))
  image[is.na(image)] <- 0
}

if(!opt$keepZeroes){
  cat(paste0("\nRemoving Zeroes... "))
  Atlas_vectorized = Atlas[Atlas!=0]
  image_matrix <- image[Atlas!=0]
} else {
  cat(paste0("\nKeeping Zeroes... "))
  Atlas_vectorized = Atlas[TRUE]
  image_matrix <- image[TRUE]
}



tic()
cat("\nCalculation results... ")
df_out <- data.frame("ROI" = ROIs)
resVals <- lapply(ROIs, function(r){
  return(do.call(opt$func, c(list(image_matrix[Atlas_vectorized == r]), argList)))
})


df_out$vals <- unlist(resVals)
toc()


write.csv(df_out, opt$out, row.names = FALSE)
cat(paste0("\nOutput written to: ", opt$out, "\n"))