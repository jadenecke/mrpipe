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
              help="Optional: Scale parameter for the phase. Set value will be used as pi: phaseScaled = angle * (scale / pi)", metavar="4096"),
  make_option(c("--checkBipolar"), action="store_true", default=FALSE,
              help="Check for alternating slice sign inversion and correct it")
)

opt_parser = OptionParser(option_list=option_list)
opt = parse_args(opt_parser)


# Check required parameters
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

if (!file.exists(opt$real)) {
  stop(paste0("Input file \"", opt$real, "\" does not exist"))
}
if (!file.exists(opt$imaginary)) {
  stop(paste0("Input file \"", opt$imaginary, "\" does not exist"))
}


require(RNifti)


# Determine phase scaling
if (is.na(opt$scale)) {
  
  if (is.na(opt$origPhase)) {
    
    warning(
      "Scale parameter not set. The returned phase image will have a ",
      "scale from -pi:pi. This might cause errors in other processing pipelines."
    )
    
    scaleParam <- pi
    
  } else {
    
    if (!file.exists(opt$origPhase)) {
      stop(paste0("Input file \"", opt$origPhase, "\" does not exist"))
    }
    
    scaleParam <- max(abs(readNifti(opt$origPhase)))
    
    cat(
      paste0(
        "Scaling angle from -pi:pi to -",
        scaleParam,
        ":",
        scaleParam,
        ". If this seems wrong to you consider specifying ",
        "your own value with --scale.\n\n"
      )
    )
  }
  
} else {
  scaleParam <- opt$scale
}


# Read real and imaginary images
real <- readNifti(opt$real)
imaginary <- readNifti(opt$imaginary)


# ------------------------------------------------------------
# Optional bipolar/readout sign check
# ------------------------------------------------------------

if (opt$checkBipolar) {
  
  cat("Checking for alternating slice sign inversion...\n")
  
  nSlices <- dim(real)[3]
  
  if (dim(imaginary)[3] != nSlices) {
    stop("Real and imaginary images have different numbers of slices")
  }
  
  # Calculate correlation between adjacent slices.
  #
  # If adjacent slices are approximately identical:
  #     cor ~ +1
  #
  # If adjacent slices are approximately negatives:
  #     cor ~ -1
  #
  realCor <- sapply(1:(nSlices - 1), function(z) {
    cor(
      as.vector(real[, , z]),
      as.vector(real[, , z + 1]),
      use = "complete.obs"
    )
  })
  
  imagCor <- sapply(1:(nSlices - 1), function(z) {
    cor(
      as.vector(imaginary[, , z]),
      as.vector(imaginary[, , z + 1]),
      use = "complete.obs"
    )
  })
  
  # We expect BOTH real and imaginary components to alternate
  # between approximately +1 and -1.
  #
  # Therefore the product should be positive and close to 1
  # when both components have the same sign inversion.
  combinedCor <- (realCor + imagCor) / 2
  
  cat("\nAdjacent-slice correlations:\n")
  print(round(combinedCor, 3))
  
  # Determine whether the correlations alternate between
  # strongly positive and strongly negative.
  #
  # threshold can be made more/less stringent if necessary.
  threshold <- 0.6
  
  if (mean(combinedCor, na.rm = TRUE) < threshold) {
    
    cat(
      "\nWARNING: Alternating sign inversion detected.\n",
      "This is consistent with a pi phase shift between alternating slices.\n",
      "Flipping both real and imaginary components on every second slice.\n\n",
      sep = ""
    )
    
    # Flip every second slice.
    #
    # Which slice is flipped depends on whether the first
    # adjacent pair is +/-. If slice 2 is the negative one,
    # flip 2,4,6,...
    #
    # If slice 1 is the negative one, flip 1,3,5,...
    ## ANSEWER: No, first slice is always in the correct direction as it is determined by the phase encoding direction.
    ## There should be no reason why the first slice is acquired on the "fly-back".
    ## Also, this is performed without mention for the QSM consensus paper, and it is regardless of Monopolar or Bipolar readout:
    ## https://github.com/kschan0214/QSM_Consensus_Paper_Example_Code/blob/main/From_DICOM_zip_file_to_SEPIA_ready/Preparation_04_prepare_for_sepia.m
    ## Seems to affect just all GE scanners by default. 
    slicesToFlip <- seq(2, nSlices, by = 2)
    
    
    real[, , slicesToFlip] <- -real[, , slicesToFlip]
    
    imaginary[, , slicesToFlip] <- -imaginary[, , slicesToFlip]
    
    cat(
      "Flipped slices: ",
      paste(slicesToFlip, collapse = ", "),
      "\n\n",
      sep = ""
    )
    
  } else {
    
    cat(
      "\nNo convincing alternating sign inversion detected.\n",
      "No correction applied.\n\n",
      sep = ""
    )
  }
}


# ------------------------------------------------------------
# Create complex image
# ------------------------------------------------------------

comp <- real + 1i * imaginary


# ------------------------------------------------------------
# Calculate magnitude and phase
# ------------------------------------------------------------

writeNifti(
  abs(comp),
  opt$magnitude,
  template = opt$real
)

writeNifti(
  Arg(comp) * (abs(scaleParam) / pi),
  opt$phase,
  template = opt$real
)


cat("Done.\n\n")