function rescaleInKSpace4D(magFilePath, phaFilePath, resultFilePathMagCropped, resultFilePathPhaCropped, tukeyStrength)
    [filepath,name,ext] = fileparts(mfilename('fullpath'))
    addpath([filepath, '/window2'])

    magHD = niftiinfo(magFilePath);

    if magHD.PixelDimensions(1) >= 0.65
        createSymbolicLink(magFilePath,resultFilePathMagCropped)
        createSymbolicLink(phaFilePath,resultFilePathPhaCropped)
        exit
    end

    magNifti4D = double(niftiread(magFilePath));
    phaNifti4D = double(niftiread(phaFilePath));
    
    nEchoes = magHD.ImageSize(4);
    
    ScaleMax = max(abs(phaNifti4D), [], 'all');
    
    kspHD = magHD;
    kspHD.Datatype = 'double';
    FOV = magHD.ImageSize(1) * magHD.PixelDimensions(1);
    newInPlaneVox = floor(floor(FOV / 0.65)/4)*4;
    newInPlaneVoxRes = FOV / newInPlaneVox;
    resDiffHalf = (magHD.ImageSize(1) - newInPlaneVox) / 2;
    
    kspHDCropped = magHD;
    kspHDCropped.Datatype = 'double';
    kspHDCropped.ImageSize = [newInPlaneVox, newInPlaneVox, kspHD.ImageSize(3), nEchoes];
    kspHDCropped.PixelDimensions = [newInPlaneVoxRes, newInPlaneVoxRes, kspHD.PixelDimensions(3), kspHD.PixelDimensions(4)];
    kspHDCropped.Transform.T(1:size(kspHDCropped.Transform.T, 1) + 1:end) = [newInPlaneVoxRes, newInPlaneVoxRes, kspHD.PixelDimensions(3), 1];
    
    magNifti4DScaled = NaN(newInPlaneVox, newInPlaneVox, kspHD.ImageSize(3), nEchoes);
    phaNifti4DScaled = NaN(newInPlaneVox, newInPlaneVox, kspHD.ImageSize(3), nEchoes);
    
    
    % Iterate over Echoes
    for j = 1:nEchoes
        phaNifti = phaNifti4D(:,:,:,j);
        magNifti = magNifti4D(:,:,:,j);
    
        % Step 1: Scale Phase to -pi:pi
        display("Scale factor is assumed to be: " + ScaleMax);
        phaNiftiScaled = (phaNifti + ScaleMax) / (ScaleMax / pi);
        
        % Step 2: Calculate complex image
        complexImage = magNifti .* exp(1i * phaNiftiScaled);
        
        % Step 3: Perform inverse 2D FFT
        ksp = fftshift(ifft2(fftshift(complexImage)));
    
        % Step 4: Crop k-space
        kspCropped = ksp(resDiffHalf + 1 : magHD.ImageSize(1) - resDiffHalf, ...
        resDiffHalf + 1 : magHD.ImageSize(1) - resDiffHalf, :);
    
        % Step 4: Tukey Filter
        tukey2d = tukey2(kspHDCropped.ImageSize(1), kspHDCropped.ImageSize(2), tukeyStrength);
        kspCroppedSmoothed = kspCropped .* tukey2d;
    
        % Step 4: Reverse FFT
        compRev = fftshift(fft2(fftshift(kspCroppedSmoothed)));
    
        % Complex to mag + pha
        magNifti4DScaled(:,:,:,j) = abs(compRev);
        phaNifti4DScaled(:,:,:,j) = ((angle(compRev) .* (ScaleMax / pi)) - ScaleMax);
    
    end

     % Remove the .nii or .nii.gz extension
    if endsWith(resultFilePathMagCropped, '.nii.gz')
        resultFilePathMagCropped = erase(resultFilePathMagCropped, '.nii.gz');
    elseif endsWith(filename, '.nii')
        resultFilePathMagCropped = erase(resultFilePathMagCropped, '.nii');
    end

    if endsWith(resultFilePathPhaCropped, '.nii.gz')
        resultFilePathPhaCropped = erase(resultFilePathPhaCropped, '.nii.gz');
    elseif endsWith(filename, '.nii')
        resultFilePathPhaCropped = erase(resultFilePathPhaCropped, '.nii');
    end
    
    magHDCropped = kspHDCropped;
    magHDCropped.Datatype = 'double';
    phaHDCropped = kspHDCropped;
    phaHDCropped.Datatype = 'int32';
    niftiwrite(magNifti4DScaled, resultFilePathMagCropped, magHDCropped, "Compressed",true);
    niftiwrite(int32(phaNifti4DScaled), resultFilePathPhaCropped, phaHDCropped, "Compressed",true);
end