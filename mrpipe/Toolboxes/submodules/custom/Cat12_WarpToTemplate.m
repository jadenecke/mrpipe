function Cat12_WarpToTemplate(image, warpfield, outfile, tempdir, interp, voxelsize)
    fprintf('Input Parameter:\nInput Image Path: %s\nWarpfield Path: %s\nOutput Image Path: %s\nTemp Dir Path: %s\n', image, warpfield, outfile, tempdir);
    
    [~, imageName, imageExt] = fileparts(image);

    % unzippedImage=false;
    unzippedWarpfield=false;
    gzipOutfile=false;
    
    % Generate a unique ID and temp directory path
    uid = char(java.util.UUID.randomUUID);
    tmpDirUID = fullfile(tempdir, uid);
    
    % Create the directory
    mkdir(tmpDirUID);
    
    % Define source file and destination
    srcFile = strcat(imageName, imageExt);
    tempFile = fullfile(tmpDirUID, srcFile);
    
    % Copy the file
    copyfile(image, tempFile);
    
    fprintf('File copied to: %s\n', tempFile);

    clear imageName imageExt image;

    [imageDir, imageName, imageExt] = fileparts(tempFile);
    if strcmp(imageExt, '.gz')
        fprintf("Unzipping Image...\n")
        gunzip(tempFile)
        tempFile = fullfile(imageDir, imageName);
        % unzippedImage=true;
    end

    [warpfieldDir, warpfieldName, warpfieldExt] = fileparts(warpfield);
    if strcmp(warpfieldExt, '.gz')
        fprintf("Unzipping Warpfield...\n")
        gunzip(warpfield)
        warpfield = fullfile(warpfieldDir, warpfieldName);
        unzippedWarpfield=true;
    end

    matlabbatch{1}.spm.tools.cat.tools.defs.field1 = {strcat(warpfield, ',1')};
    matlabbatch{1}.spm.tools.cat.tools.defs.images = {strcat(tempFile, ',1')};
    matlabbatch{1}.spm.tools.cat.tools.defs.bb = [NaN NaN NaN
                                              NaN NaN NaN];
    matlabbatch{1}.spm.tools.cat.tools.defs.vox = [voxelsize voxelsize voxelsize];
    matlabbatch{1}.spm.tools.cat.tools.defs.interp = interp; %0 == NN; 3 == 3rd degree B-Spline
    matlabbatch{1}.spm.tools.cat.tools.defs.modulate = 0;

    % run matlabbatch
    fprintf("Warping...\n")
    spm_jobman('run', matlabbatch)

    % exit matlab
    pause(5)
    
    [filepath,name,ext] = fileparts(tempFile);
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
    
    % if unzippedImage
    %     if isfile(strcat(tempFile, '.gz'))
    %         fprintf("deleting unzipped Image ...\n")
    %         delete(tempFile)
    %     else
    %          fprintf("gzipping Image ...\n")
    %         gzip(tempFile)
    %     end
    % end
    fprintf("deleting temp files ...\n")
    delete(tempFile)
    rmdir(tmpDirUID)
    
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

