function denoise_AONLM_cmd(infile, outfile, rician, packagepath)
% Pierrick Coupe - pierrick.coupe@gmail.com
% Jose V. Manjon - jmanjon@fis.upv.es
% LaBRI UMR 5800
% Universite de Bordeaux 1
%
% Copyright (C) 2008-2013 Pierrick Coupe and Jose V. Manjon
% ***************************************************************************/

    addpath(genpath(packagepath));
    %method=2;

    %set parameter here because matlab
    beta = 1;
    patchradius = 1;
    searchradius = 3;
    verbose = 1;

    com = sprintf('beta: %0.1f', beta);
    disp(com)
    com = sprintf('patch size: %dx%dx%d voxels', 2*patchradius+1, 2*patchradius+1, 2*patchradius+1);
    disp(com)
    com = sprintf('search volume size: %dx%dx%d voxels', 2*searchradius+1, 2*searchradius+1, 2*searchradius+1);
    disp(com)


    if (rician==1)
        com = sprintf('Rician noise model\n');
        disp(com)
    else
        com = sprintf('Gaussian noise model\n');
        disp(com)
    end



    disp(['Input file : ', infile])
    disp(['Output file: ', outfile])

    VI=niftiinfo(infile);
    ima=niftiread(VI);
    s=size(ima);

    if class(ima) == "int16"
        ima = single(ima);
    end

    % fixed range
    map = isnan(ima(:));
    ima(map) = 0;
    map = isinf(ima(:));
    ima(map) = 0;
    mini = min(ima(:));
    ima = ima - mini;
    maxi=max(ima(:));
    ima=ima*256/maxi;


    MRIdenoised = MRIDenoisingAONLM(ima, patchradius,  searchradius, beta, rician, verbose);
    map = find(MRIdenoised<0);
    MRIdenoised(map)=0;

    % Original intensity range
    MRIdenoised= MRIdenoised*maxi/256;
    MRIdenoised =MRIdenoised + mini;


    VO = VI; % copy input info for output image

    VO.Filename=outfile;
    VO.ImageSize=s;
    VO.Datatype=class(MRIdenoised);
    niftiwrite(MRIdenoised, outfile, VO, 'Compressed', true);
end
