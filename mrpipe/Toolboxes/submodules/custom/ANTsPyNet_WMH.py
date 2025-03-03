#!/usr/bin/env python3


def shivai(t1, flair):
	return antspynet.shiva_wmh_segmentation(flair, t1, which_model="all", verbose=True)

def sysu_media(t1, flair):
	return antspynet.sysu_media_wmh_segmentation(flair, t1, verbose=True)

def hypermapp3r(t1, flair):
	return antspynet.hypermapp3r_segmentation(t1, flair, verbose=True)

def ants_xnet(t1, flair):
    t1 = ants.resample_image(t1, (240, 240, 64), use_voxels=True)
    flair = ants.resample_image(flair, (240, 240, 64), use_voxels=True)
    return antspynet.wmh_segmentation(flair, t1, use_combined_model=True, verbose=True)

def shiva_pvs(t1, flair):
    return antspynet.shiva_pvs_segmentation(t1, flair, which_model="all", verbose=True)


def wmhs_segmentation(t1_path, flair_path, output, pipelines):
    
    
    # Load the images
    t1 = ants.image_read(t1_path)
    flair = ants.image_read(flair_path)
    
    # Create a dictionary to map pipeline names to their corresponding functions
    pipeline_dict = {
        'shivai': shivai,
        'sysu_media': sysu_media,
        'hypermapp3r': hypermapp3r,
        'ants_xnet': ants_xnet,
        'shiva_pvs': shiva_pvs,
    }
    
    # Perform WMH segmentation using selected pipelines
    for pipeline in pipelines:
        if pipeline in pipeline_dict:
            wmh = pipeline_dict[pipeline](t1, flair)
            wmh_path = f"{output}{pipeline}.nii.gz"
            ants.image_write(wmh, wmh_path)
            print(f"WMH segmentation using {pipeline} saved to {wmh_path}")
        else:
            print(f"Pipeline {pipeline} not recognized")  

if __name__ == "__main__":
    import argparse
    # Set up argument parser
    parser = argparse.ArgumentParser(description='WMH Segmentation using ANTsPyNet')
    parser.add_argument('-t1', '--t1_image', required=True, help='Path to T1 image')
    parser.add_argument('-f', '--flair_image', required=True, help='Path to FLAIR image')
    parser.add_argument('-o', '--output', required=True, help='Output pre-string, e.g. path/to/sub_ses_')
    parser.add_argument('-p', '--pipelines', nargs='+', required=True, 
                        choices=['shivai', 'sysu_media', 'hypermapp3r', 'ants_xnet', 'shiva_pvs'], 
                        help='List of pipelines to use for WMH segmentation')

    # Parse arguments
    args = parser.parse_args()
    
    
    # Run the segmentation
    import ants
    import antspynet
    wmhs_segmentation(args.t1_image, args.flair_image, args.output, args.pipelines)
    
