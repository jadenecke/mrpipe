function rescaleInKSpace(mag4D_path, phs4D_path, inPlaneMaxRes, tukeySize, outMag4DPath, outPha4DPath)
% Takes 4D magnitude and phase data, transforms it to kspace, crops border
% to achieve new resolution, applies tuky filter and transforms back to
% magnitude and phase data with new resolution.

    %addpath('window2')

    magHD4D = niftiinfo(mag4D_path);
    phaHD4D = niftiinfo(phs4D_path);


    FOVx = magHD4D.ImageSize(1) * magHD4D.PixelDimensions(1);
    FOVy = magHD4D.ImageSize(2) * magHD4D.PixelDimensions(2);
    display("Image FOV: " + FOVx + " / " + FOVy);

    newInPlaneVoxx = floor(floor(FOVx / inPlaneMaxRes)/4)*4;
    newInPlaneVoxy = floor(floor(FOVy / inPlaneMaxRes)/4)*4;
    
    %limit in case of lower resolution:
    newInPlaneVoxx = min(magHD4D.ImageSize(1), newInPlaneVoxx);
    newInPlaneVoxy = min(magHD4D.ImageSize(2), newInPlaneVoxy);
    newInPlaneVoxResx = FOVx / newInPlaneVoxx;
    newInPlaneVoxResy = FOVy / newInPlaneVoxy;
    resDiffHalfx = (magHD4D.ImageSize(1) - newInPlaneVoxx) / 2;
    resDiffHalfy = (magHD4D.ImageSize(2) - newInPlaneVoxy) / 2;

    display("Old in-plane resolution: " + magHD4D.PixelDimensions(1) + "/" + magHD4D.PixelDimensions(2))
    display("New in-plane resolution: " + newInPlaneVoxResx + "/" + newInPlaneVoxResy)
    
    if resDiffHalfx == 0 && resDiffHalfy == 0
        display("Image resolution is lower then requested resolution. Not doing anything. Exiting now...")
        return
    end
    magNifti4D = double(niftiread(mag4D_path));
    phaNifti4D = double(niftiread(phs4D_path));
    magOut4D = createArray(newInPlaneVoxx, newInPlaneVoxy, size(magNifti4D, 3), size(magNifti4D, 4), "double");
    phaOut4D = createArray(newInPlaneVoxx, newInPlaneVoxy, size(phaNifti4D, 3), size(phaNifti4D, 4), "int32");
    
    %ScaleMax = abs(phaHD4D.AdditiveOffset); %does not work after fslmerge anymore as it does not copy additiveOffset nor multiplicativeScaling
    ScaleMax = max(abs(phaNifti4D), [], 'all');
    display("Scale factor is assumed to be: " + ScaleMax);

    % Iterate over magFiles and phaFiles
    for j = 1:size(magNifti4D, 4)
        display("Echo Number: " + j);
        % Load magnitude and phase NIfTI files
        magNifti=magNifti4D(:,:,:,j);
        phaNifti=phaNifti4D(:,:,:,j);

        % Step 1: Scale Phase to -pi:pi
        %phaNiftiScaled = (phaNifti * phaHD4D.MultiplicativeScaling + phaHD4D.AdditiveOffset) / (ScaleMax / pi);
        phaNiftiScaled = phaNifti / (ScaleMax / pi);

        % Step 2: Calculate complex image
        complexImage = magNifti .* exp(1i * phaNiftiScaled);

        % Step 3: Perform inverse 2D FFT
        ksp = fftshift(ifft2(fftshift(complexImage)));

        kspCropped = ksp(resDiffHalfx + 1 : magHD4D.ImageSize(1) - resDiffHalfx, ...
            resDiffHalfy + 1 : magHD4D.ImageSize(2) - resDiffHalfy, :);
     
        tukey2d = tukey2(newInPlaneVoxx, newInPlaneVoxy, tukeySize);
        kspCroppedSmoothed = kspCropped .* tukey2d;
        %niftiwrite(kspCroppedSmoothed, resultFilePathKspCroppedSmoothed, kspHDCropped);

        % reverse
        compRev = fftshift(fft2(fftshift(kspCroppedSmoothed)));
        magOut4D(:,:,:,j) = abs(compRev);
        %phaOut4D(:,:,:,j) = int32(((angle(compRev) .* (ScaleMax / pi)) - phaHD4D.AdditiveOffset) / phaHD4D.MultiplicativeScaling);
        phaOut4D(:,:,:,j) = int32(angle(compRev) .* (ScaleMax / pi));
    
    end
    
    magHD4Dcropped = magHD4D;
    magHD4Dcropped.Filename = outMag4DPath;
    magHD4Dcropped.ImageSize = size(magOut4D);
    magHD4Dcropped.PixelDimensions = [newInPlaneVoxResx, newInPlaneVoxResy, magHD4D.PixelDimensions(3), magHD4D.PixelDimensions(4)];
    magHD4Dcropped.Transform.T(1:size(magHD4Dcropped.Transform.T, 1) + 1:end) = [newInPlaneVoxResx, newInPlaneVoxResy, magHD4D.PixelDimensions(3), 1];
    magHD4Dcropped.Datatype = 'double';

    phaHD4Dcropped = phaHD4D;
    phaHD4Dcropped.Filename = outPha4DPath;
    phaHD4Dcropped.ImageSize = size(phaOut4D);
    phaHD4Dcropped.PixelDimensions = [newInPlaneVoxResx, newInPlaneVoxResy, phaHD4D.PixelDimensions(3), phaHD4D.PixelDimensions(3)];
    phaHD4Dcropped.Transform.T(1:size(phaHD4Dcropped.Transform.T, 1) + 1:end) = [newInPlaneVoxResx, newInPlaneVoxResy, phaHD4D.PixelDimensions(3), 1];
    phaHD4Dcropped.Datatype = 'int32';
    % phaHD4Dcropped.AdditiveOffset = phaHD4D.AdditiveOffset;
    % phaHD4Dcropped.MultiplicativeScaling = phaHD4D.MultiplicativeScaling;

    niftiwrite(magOut4D, outMag4DPath, magHD4Dcropped);
    niftiwrite(phaOut4D, outPha4DPath, phaHD4Dcropped);
end

