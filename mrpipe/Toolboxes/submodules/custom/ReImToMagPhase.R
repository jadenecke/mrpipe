#!/usr/bin/env Rscript
library("optparse")

option_list = list(
  make_option(c("-r", "--real"), type="character", default=NA, 
              help="name of real component image", metavar="real.nii.gz"),
  make_option(c("-i", "--imaginary"), type="character", default=NA, 
              help="name of imaginary component image", metavar="imaginary.nii.gz"),
   make_option(c("-m", "--magnitude"), type="character", default=NA, 
              help="output name of magnitude image", metavar="magnitude.nii.gz"),
  make_option(c("-p", "--phase"), type="character", default=NA, 
              help="output name of phase image", metavar="phase.nii.gz"),
  make_option(c("-o", "--origPhase"), type="character", default=NA, 
              help="name of original phase. Required to scale from -pi:pi to originals values. Might or might not be required.", metavar="phase.nii.gz"),
  make_option(c("-s", "--scale"), type="numeric", default=NA, 
              help="Optional: Scale parameter for the phase. Set value will be used as pi: phaseScaled =  angle * (scale / pi)", metavar="4096")
)
opt_parser = OptionParser(option_list=option_list)
opt = parse_args(opt_parser)

# check date is provided
if (is.na(opt$magnitude)) {
  stop("magnitude parameter must be provided. See script usage (--help)")
}
if (is.na(opt$phase)) {
  stop("phase parameter must be provided. See script usage (--help)")
}
if (is.na(opt$real)) {
  stop("real parameter must be provided. See script usage (--help)")
}
if (is.na(opt$imaginary)) {
  stop("imaginary parameter must be provided. See script usage (--help)")
}
if(!file.exists(opt$real)){
  stop(paste0("Input file \"",opt$real, "\" does not exist"))
}
if(!file.exists(opt$imaginary)){
  stop(paste0("Input file \"", opt$imaginary, "\" does not exist"))
}


require(RNifti)


if(is.na(opt$scale)){
  if(is.na(opt$origPhase)){
    warning("Scale parameter not set. The returned phase image will have a scale from -pi:pi. This might cause errors in other processing piplines.")
    scaleParam <- pi
  } else {
    if(!file.exists(opt$origPhase)){
      stop(paste0("Input file \"",opt$origPhase, "\" does not exist"))
    }
    scaleParam <- max(abs(readNifti(opt$origPhase)))
    cat(paste0("Scaling angle from -pi:p to -", scaleParam, ":", scaleParam, ". If this seems wrong to you consider specifying your own value with --scale.\n\n"))
  }
} else {
  scaleParam <- opt$scale
}

real <- readNifti(opt$real)
imaginary <- readNifti(opt$imaginary)

comp <- real + 1i * imaginary


writeNifti(abs(comp), opt$magnitude, template = opt$real)  
writeNifti(Arg(comp) * (abs(scaleParam) / pi), opt$phase, template = opt$real) 

cat(paste0("Done.\n\n"))