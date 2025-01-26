#!/usr/bin/env Rscript
library("optparse")

option_list = list(
  make_option(c("-i", "--inVal"), type="numeric", default=NA,
              help="Input Value", metavar="suvr"),
  make_option(c("-t", "--tracer"), type="character", default=NA,
              help="Tracer name, one of [RO948, FTP, MK6240, GTP1, PM-PBB3, PI2620]", metavar="name"),
  make_option(c("-m", "--mask"), type="character", default=NA,
              help="Tracer name, one of [CenTauR, Frontal_CenTauR, Mesial_CenTauR, Meta_CenTauR, TP_CenTauR]", metavar="name"),
  make_option(c("-o", "--outFile"), type="character", default=NA,
              help="If specified, output value is not returned to stdOut but to file.", metavar="CTRz.csv")
)

opt_parser = OptionParser(option_list=option_list, description = "This function takes a SUVR numeric value and returns a CenTauRz score")
opt = parse_args(opt_parser)


# check data is provided --------------------------------------------
if (is.na(opt$inVal)) {
  stop("Input file name must be provided. See script usage (--help)")
}
if (is.na(opt$tracer)) {
  stop("Tracer name must be provided. See script usage (--help)")
}
if (is.na(opt$mask)) {
  stop("Tracer name must be provided. See script usage (--help)")
}

if(!is.numeric(opt$inVal)){
  stop(paste0("Input value \"",opt$file, "\" is not numeric"))
}

opt$tracer <- toupper(opt$tracer)
validTracer <- c("RO948", "FTP", "MK6240", "GTP1", "PM-PBB3", "PI2620")
validMasks <- c("CenTauR", "Frontal_CenTauR", "Mesial_CenTauR", "Meta_CenTauR", "TP_CenTauR")
if (!(opt$tracer %in% validTracer)){
  stop(paste0("Tracer ", opt$tracer, " is not a valid tracer. Valid Tracers are: ", paste0(validTracer, collapse = ", ")))
}
if (!(opt$mask %in% validMasks)){
  stop(paste0("Mask ", opt$mask, " is not a valid tracer. Valid Tracers are: ", paste0(validMasks, collapse = ", ")))
}


# actual calculations --------------------------------------------

if (opt$tracer == "RO948"){
    if ( opt$mask == "CenTauR"){
        CTRz <- 13.05 * opt$inVal - 15.57
    } else if (opt$mask == "Mesial_CenTauR"){
        CTRz <- 11.76 * opt$inVal - 13.08
    } else if (opt$mask == "Meta_CenTauR"){
        CTRz <- 13.16 * opt$inVal - 16.19
    } else if (opt$mask == "TP_CenTauR"){
        CTRz <- 13.05 * opt$inVal - 15.62
    } else if (opt$mask == "Frontal_CenTauR"){
        CTRz <- 12.61 * opt$inVal - 13.45
    } else {
        stop(paste0("Mask ", opt$mask, " is not a valid tracer. Valid Tracers are: ", paste0(validMasks, collapse = ", ")))
    }
} else if (opt$tracer == "FTP"){
    if ( opt$mask == "CenTauR"){
        CTRz <- 13.63 * opt$inVal - 15.85
    } else if (opt$mask == "Mesial_CenTauR"){
        CTRz <- 10.42 * opt$inVal - 12.11
    } else if (opt$mask == "Meta_CenTauR"){
        CTRz <- 12.95 * opt$inVal - 15.37
    } else if (opt$mask == "TP_CenTauR"){
        CTRz <- 13.75 * opt$inVal - 15.92
    } else if (opt$mask == "Frontal_CenTauR"){
        CTRz <- 11.61 * opt$inVal - 13.01
    } else {
        stop(paste0("Mask ", opt$mask, " is not a valid tracer. Valid Tracers are: ", paste0(validMasks, collapse = ", ")))
    }
} else if (opt$tracer == "MK6240"){
    if ( opt$mask == "CenTauR"){
        CTRz <- 10.08 * opt$inVal - 10.06
    } else if (opt$mask == "Mesial_CenTauR"){
        CTRz <- 7.28 * opt$inVal - 7.01
    } else if (opt$mask == "Meta_CenTauR"){
        CTRz <- 9.36 * opt$inVal - 10.6
    } else if (opt$mask == "TP_CenTauR"){
        CTRz <- 9.98 * opt$inVal - 10.15
    } else if (opt$mask == "Frontal_CenTauR"){
        CTRz <- 10.05 * opt$inVal - 8.91
    } else {
        stop(paste0("Mask ", opt$mask, " is not a valid tracer. Valid Tracers are: ", paste0(validMasks, collapse = ", ")))
    }
} else if (opt$tracer == "GTP1"){
    if ( opt$mask == "CenTauR"){
        CTRz <- 10.67 * opt$inVal - 11.92
    } else if (opt$mask == "Mesial_CenTauR"){
        CTRz <- 7.88 * opt$inVal - 8.75
    } else if (opt$mask == "Meta_CenTauR"){
        CTRz <- 9.60 * opt$inVal - 11.10
    } else if (opt$mask == "TP_CenTauR"){
        CTRz <- 10.84 * opt$inVal - 12.27
    } else if (opt$mask == "Frontal_CenTauR"){
        CTRz <- 9.41 * opt$inVal - 9.71
    } else {
        stop(paste0("Mask ", opt$mask, " is not a valid tracer. Valid Tracers are: ", paste0(validMasks, collapse = ", ")))
    }
} else if (opt$tracer == "PM-PBB3"){
    if ( opt$mask == "CenTauR"){
        CTRz <- 16.73 * opt$inVal - 15.34
    } else if (opt$mask == "Mesial_CenTauR"){
        CTRz <- 7.97 * opt$inVal - 7.83
    } else if (opt$mask == "Meta_CenTauR"){
        CTRz <- 11.78 * opt$inVal - 11.21
    } else if (opt$mask == "TP_CenTauR"){
        CTRz <- 16.16 * opt$inVal - 14.68
    } else if (opt$mask == "Frontal_CenTauR"){
        CTRz <- 15.7 * opt$inVal - 13.18
    } else {
        stop(paste0("Mask ", opt$mask, " is not a valid tracer. Valid Tracers are: ", paste0(validMasks, collapse = ", ")))
    }
} else if (opt$tracer == "PI2620"){
    if ( opt$mask == "CenTauR"){
        CTRz <- 8.45 * opt$inVal - 9.61
    } else if (opt$mask == "Mesial_CenTauR"){
        CTRz <- 6.03 * opt$inVal - 6.83
    } else if (opt$mask == "Meta_CenTauR"){
        CTRz <- 7.78 * opt$inVal - 9.33
    } else if (opt$mask == "TP_CenTauR"){
        CTRz <- 8.21 * opt$inVal - 9.52
    } else if (opt$mask == "Frontal_CenTauR"){
        CTRz <- 9.07 * opt$inVal - 9.01
    } else {
        stop(paste0("Mask ", opt$mask, " is not a valid tracer. Valid Tracers are: ", paste0(validMasks, collapse = ", ")))
    }
} else {
  stop(paste0("Tracer ", opt$tracer, " is not a valid tracer. Valid Tracers are: ", paste0(validTracer, collapse = ", ")))
}


if (!is.na(opt$outFile)){
    dfOut <- data.frame(x = CTRz)
    names(dfOut) <- paste("CTRz_", opt$mask)
    write.csv(dfOut, opt$outFile, row.names = FALSE)
} else {
    cat(CTRz)
}

