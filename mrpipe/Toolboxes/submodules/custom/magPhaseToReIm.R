#!/usr/bin/env Rscript
library("optparse")

option_list = list(
  make_option(c("-m", "--magnitude"), type="character", default=NA, 
              help="magnitude image path", metavar="magnitude.nii.gz"),
  make_option(c("-p", "--phase"), type="character", default=NA, 
              help="phase image path", metavar="phase.nii.gz"),
  make_option(c("-r", "--real"), type="character", default=NA, 
              help="output name of real component image", metavar="real.nii.gz"),
  make_option(c("-i", "--imaginary"), type="character", default=NA, 
              help="output name of imaginary component image", metavar="imaginary.nii.gz"),
  make_option(c("-c", "--complex"), type="character", default=NA, 
              help="Optional: Write complex image. ", metavar="imaginary.nii.gz"),
  make_option(c("--complex128"), type="logical", default=FALSE, action = "store_true",
              help="Optional: Use Complex128 encoding for complex file. Note that FSLcomplex only works with complex64 encoding which is the default for this script.", metavar="FALSE"),
  make_option(c("-s", "--scale"), type="numeric", default=NA, 
              help="Optional: Scale parameter for the phase. Set value will be used as pi: phaseScaled =  phase / (scale / pi)", metavar="4096")
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
if(!file.exists(opt$magnitude)){
  stop(paste0("Input file \"",opt$magnitude, "\" does not exist"))
}
if(!file.exists(opt$phase)){
  stop(paste0("Input file \"", opt$phase, "\" does not exist"))
}


if(opt$complex128){
  dataType <- "COMPLEX128"
  cat(paste0("Using complex128 as encoding for the complex image. This datatype might not work for all image processing libraries.\n\n"))
} else {
  dataType <- "COMPLEX64" 
}

require(RNifti)


mag <- readNifti(opt$magnitude)
pha <- readNifti(opt$phase)

if(is.na(opt$scale)){
  scaleParam <- max(abs(pha))
  cat(paste0("Scaling phase image to -pi:pi. Scaling ", scaleParam, " to pi. If this seems wrong to you consider specifying your own value with --scale.\n\n"))
} else {
  scaleParam <- opt$scale
}


comp <- mag * exp(1i * (pha / (scaleParam / pi)))

if(!is.na(opt$complex)){
  writeNifti(comp, opt$complex, datatype = dataType, template = opt$magnitude)  
}

writeNifti(Re(comp), opt$real, template = opt$magnitude)  
writeNifti(Im(comp), opt$imaginary, template = opt$magnitude) 

cat(paste0("Done.\n\n"))