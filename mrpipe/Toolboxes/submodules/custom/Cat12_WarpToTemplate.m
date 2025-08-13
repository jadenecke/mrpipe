function Cat12_WarpToTemplate(image, warpfield, outfile, interp)
    fprintf('Input Parameter:\nInput Image Path: %s\nWarpfield Path: %s\nOutput Image Path: %s\n', image, warpfield, outfile);

    unzippedImage=false;
    unzippedWarpfield=false;
    gzipOutfile=false;

    [imageDir, imageName, imageExt] = fileparts(image);
    if strcmp(imageExt, '.gz')
        fprintf("Unzipping Image...\n")
        gunzip(image)
        image = fullfile(imageDir, imageName);
        unzippedImage=true;
    end

    [warpfieldDir, warpfieldName, warpfieldExt] = fileparts(warpfield);
    if strcmp(warpfieldExt, '.gz')
        fprintf("Unzipping Warpfield...\n")
        gunzip(warpfield)
        warpfield = fullfile(warpfieldDir, warpfieldName);
        unzippedWarpfield=true;
    end

    matlabbatch{1}.spm.tools.cat.tools.defs.field1 = {strcat(warpfield, ',1')};
    matlabbatch{1}.spm.tools.cat.tools.defs.images = {strcat(image, ',1')};
    matlabbatch{1}.spm.tools.cat.tools.defs.bb = [NaN NaN NaN
                                              NaN NaN NaN];
    matlabbatch{1}.spm.tools.cat.tools.defs.vox = [NaN NaN NaN];
    matlabbatch{1}.spm.tools.cat.tools.defs.interp = interp; %0 == NN; 3 == 3rd degree B-Spline
    matlabbatch{1}.spm.tools.cat.tools.defs.modulate = 0;

    % run matlabbatch
    fprintf("Warping...\n")
    spm_jobman('run', matlabbatch)

    % exit matlab
    pause(5)
    
    [filepath,name,ext] = fileparts(image);
    imageNativeOut = fullfile(filepath, strcat('w', name, ext));
    
    fprintf("Moving output file...\n")
    
    [outDir, outName, outExt] = fileparts(outfile);
    if strcmp(outExt, '.gz')
        gzipOutfile=true;
        outfile = fullfile(outDir, outName);
    end
    
    [status,message,messageId] = movefile(imageNativeOut, outfile);
    display(strcat('Status:', int2str(status)))
    
    if ~status && ~isempty(messageId)
        fprintf('Error occurred:\nMessage ID: %s\nMessage: %s\n', messageId, message);
    end
    
    if status & gzipOutfile
        fprintf("gzipping output...\n")
        gzip(outfile)
        delete(outfile) 
    end
    
    if unzippedImage
        if isfile(strcat(image, '.gz'))
            fprintf("deleting unzipped Image ...\n")
            delete(image)
        else
             fprintf("gzipping Image ...\n")
            gzip(image)
        end
    end
    
    if unzippedWarpfield 
        if isfile(strcat(warpfield, '.gz'))
            fprintf("deleting unzipped warpfield ...\n")
            delete(warpfield)
        else
             fprintf("gzipping warpfield ...\n")
            gzip(warpfield)
        end
    end
    fprintf("All done.\n")
end

