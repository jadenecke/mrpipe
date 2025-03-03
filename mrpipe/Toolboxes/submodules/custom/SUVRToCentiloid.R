#!/usr/bin/env Rscript
library("optparse")
library("RNifti")
library("data.table")
require(tictoc, quietly = TRUE)

option_list = list(
  make_option(c("-i", "--in_file"), type="character", default=NA, 
              help="Input file name", metavar="SUVR.csv"),
  make_option(c("-o", "--out"), type="character", default=NA, 
              help="Output file name", metavar="Centiloid.csv"),
  make_option(c("-t", "--tracer"), type="character", default=NA,
              help="Tracer name, one of [FBB, AV45, NAV4694, PIB, FMM]", metavar="name")
)

opt_parser = OptionParser(option_list=option_list, description = "This function takes a two column csv with the first being ROI and the second being SUVR and adds a third column with centiloid values.")
opt = parse_args(opt_parser)


# check data is provided --------------------------------------------
if (is.na(opt$in_file)) {
  stop("Input file name must be provided. See script usage (--help)")
}
if (is.na(opt$tracer)) {
  stop("Tracer name must be provided. See script usage (--help)")
}
if (is.na(opt$out)) {
  stop("Output file name must be provided. See script usage (--help)")
}


if(!file.exists(opt$in_file)){
  stop(paste0("Input file \"",opt$file, "\" does not exist"))
}
opt$tracer <- toupper(opt$tracer)
validTracer <- c("FBB", "AV45", "NAV4694", "PIB", "FMM")
if (!(opt$tracer %in% validTracer)){
  stop(paste0("Tracer ", opt$tracer, " is not a valid tracer. Valid Tracers are: ", paste0(validTracer, collapse = ", ")))
}

cat("\nReading Input:" )
df_SUVR <- as.data.frame(fread(opt$in_file))

if (ncol(df_SUVR) != 2){
  stop(paste0("Input file \"",opt$file, "\" does not have exactly two columns"))
}

if (!unlist(apply(df_SUVR, 2, is.numeric))[2]){
  stop(paste0("Input files \"",opt$file, "\" second column is not numeric."))
}

# actual calculations --------------------------------------------

if (opt$tracer == "FBB"){
  df_SUVR$Centiloid <- 153.4 * df_SUVR[,2] - 154.9 # https://doi.org/10.1007/s00259-017-3749-6
} else if (opt$tracer == "AV45"){
  df_SUVR$Centiloid <- 183 * df_SUVR[,2] - 177 # https://doi.org/10.1016/j.jalz.2018.06.1353
} else if (opt$tracer == "NAV4694"){
  df_SUVR$Centiloid <- 100 * (df_SUVR[,2] - 1.028)/1.174  # https://doi.org/10.2967/jnumed.115.171595
} else if (opt$tracer == "PIB"){
  df_SUVR$Centiloid <- 100 * (df_SUVR[,2] - 1.009)/1.067 # https://doi.org/10.2967/jnumed.115.171595
} else if (opt$tracer == "FMM"){
  df_SUVR$Centiloid <- 148.52 * df_SUVR[,2] - 137.09 # https://doi.org/10.1007/s00259-019-04596-x
} else {
  stop(paste0("Tracer ", opt$tracer, "is not a valid tracer. Valid Tracers are: ", paste0(validTracer, collapse = ", ")))
}



write.csv(df_SUVR, opt$out, row.names = FALSE)
cat(paste0("\nOutput written to: ", opt$out, "\n"))