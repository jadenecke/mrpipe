function Chisep_script_wResolGen(mag_path, phs_path, brainmask_path, outdir, TEms, B0_direction, CFs, Toolboxes, preString, chiSepDir, vendor)
%% χ-separation Tool

% This tool is MATLAB-based software forseparating para- and dia-magnetic susceptibility sources (χ-separation). 
% Separating paramagnetic (e.g., iron) and diamagnetic (e.g., myelin) susceptibility sources 
% co-existing in a voxel provides the distributions of two sources that QSM does not provides. 

% χ-separation tool v1.0

% Contact E-mail: snu.list.software@gmail.com 

% Reference
% H.-G. Shin, J. Lee, Y. H. Yun, S. H. Yoo, J. Jang, S.-H. Oh, Y. Nam, S. Jung, S. Kim, F. Masaki, W. 
% Kim, H. J. Choi, J. Lee. χ-separation: Magnetic susceptibility source separation toward iron and 
% myelin mapping in the brain. Neuroimage, 2021 Oct; 240:118371.

% χ-separation tool is powered by MEDI toolbox (for BET and Complex data fitting), STI Suite (for V-SHARP), SEGUE toolbox (for SEGUE), and mritools (for ROMEO).


%% Example
% This example reconstructs χ-separation maps from multi-echo gradient 
% echo magnitude and phase data

%% Necessary preparation
Toolboxes = string(Toolboxes);
for i = 1:numel(Toolboxes) 
    path = Toolboxes(i);
    disp(strcat("Adding Toolbox path: ", path));
    addpath(genpath(path))
end
addpath(genpath(chiSepDir))
% x-separation tool directory path
% STISuite / MEDIToolbox / SEGUE (optional i think) / mritools (ROMEO)/
% Deep Learning Toolbox Converter for ONNX Model Format  / dicm2nii
% (optional) / Tools for NIfTI and ANALYZE image (https://kr.mathworks.com/matlabcentral/fileexchange/8797-tools-for-nifti-and-analyze-image)

%% Diagnostics

voxel_size = niftiinfo(mag_path).PixelDimensions(1:3);

disp(strcat("################# Input Data #################"));
disp(strcat("Magnitude File: ", mag_path));
disp(strcat("Phase File: ", phs_path));
disp(strcat("Brain Mask File: ", brainmask_path));
%disp(strcat("CSF Mask File: ", csfmask_path));
disp(strcat("Output Directory: ", outdir));
disp(strcat("TE: ", num2str(TEms)));
disp(strcat("CF: ", num2str(CFs)));
disp(strcat("B0 Direction: ", num2str(B0_direction)));
disp(strcat("Voxel size: ", num2str(voxel_size)));
disp(strcat("Toolbox Path: ", Toolboxes));
disp(strcat("Filename Prefix: ", preString));
disp(strcat("##############################################"));

%% Input data
% mag_multi_echo - multi-echo magnitude data (x, y, z, te)
% phs_multi_echo - multi-echo phase data (x, y, z, te)

% r2prime - R2' map in Hz unit (x, y, z). If you don't have R2' map, use
% chi-sepnet-R2* which doesn't require R2' map.

%% Data paramters
% B0_strength, B0_direction, CF (central frequency), TE (echo time), delta_TE, voxel_size

% B0_direction = [0, 0, 1];
% CF = 123200000; in Hz unit
% TE = [0.00xx, 0.00xx, 0.00xx, 0.00xx, ...]; % in [s] unit
% delta_TE = 0.00xx; % in [s] unit
% voxel_size = [dx, dy, dz]; % in [mm] unit

%% Data paramters
% B0_strength, B0_direction, CF (central frequency), TE (echo time), delta_TE, voxel_size
CF = CFs * 1e6;
B0_strength = CF / (42.57478 * 1e6);
%B0_direction = [0, 0, 1];
%CF = 123200000;
TE = TEms / 1000; %/1000 when from the swi-to-chisep script, because there it is in miliseconds
disp("TODO double check this")
delta_TE = mean(diff(TE));
%delta_TE = 4.9;
%voxel_size = [1, 1, 1];
disp(strcat("TE: ", num2str(TE)));
disp(strcat("TE delta: ", num2str(delta_TE)))

%% Load Data
disp('Loading files');
phs_multi_echo = double(niftiread(phs_path));
mask_brain = double(niftiread(brainmask_path));
mag_multi_echo = double(niftiread(mag_path));
% mask_CSF = niftiread(csfmask_path);

%% Preprocessing
% Tukey windowing
if(vendor == "Philips")
    tukey_fac = 0;
elseif(vendor == "GE" || vendor == "Siemens" )
    tukey_fac = 0.4; % Recommendation: Siemens, GE: 0.4, Philips: 0
else 
    disp("WARNING: Scanner Vendor is not GE, Philips, or Siemens, no recommendation for tukey factor, setting to 0.4, i.e. Siemens/GE recommendation.")
    tukey_fac = 0.4;
end
% img_tukey = tukey_windowing(mag_multi_echo .* exp(1i*phs_multi_echo),tukey_fac);
% mag_multi_echo = abs(img_tukey);
% phs_multi_echo = angle(img_tukey);
% Compute single magnitude data
mag = sqrt(sum(abs(mag_multi_echo).^2,4));
matrix_size = size(mag);
disp(matrix_size);
disp(size(mag_multi_echo));
[~, N_std] = Preprocessing4Phase(mag_multi_echo, phs_multi_echo); %dunno what that does, but I save it. Its only needed for processing where r2prime, i.e. spin echo data is available.

%% Generate Mask
% BET from MEDI toolbox
% NOT NEEDED because comes from input
% matrix_size = size(mag);
% mask_brain = BET(mag,matrix_size,voxel_size);

%% R2* mapping
% Compute R2* (need multi-echo GRE magnitude)

% check if arlo can be used: > 3 echos with "roughly" equidistant TE
if((length(TE) > 3) && (all(abs(mean(diff(TE)) - diff(TE)) < 0.0001)))
    use_arloFIX = true;
else
    use_arloFIX = false;
end

%if(use_arlo(TE))
if(use_arloFIX)
    % Use ARLO (More than three equi-spaced TE needed)
    r2star = r2star_arlo(mag_multi_echo,TE*1000,mask_brain); % Convert TE to [ms]
else
% Use NNLS fitting (When ARLO is not an option)
    r2star = r2star_nnls(mag_multi_echo,TE*1000,mask_brain); % Convert TE to [ms]
end

%% Compute CSF mask (Needed for Chi-separation-MEDI and Chi-separation iLSQR)
% mask_CSF = extract_CSF(r2star, mask_brain_new, voxel_size);

%% Phase unwrapping and Echo combination
% 1. ROMEO + weighted echo averaging 
parameters.TE = TE * 1000; % Convert to ms
parameters.mag = mag_multi_echo;
parameters.command = "romeo";
parameters.mask = double(mask_brain);
parameters.calculate_B0 = true;
parameters.phase_offset_correction = 'on';
parameters.voxel_size = voxel_size;
parameters.additional_flags = '-q';%'--verbose -q -i'; % settings are pasted directly to ROMEO cmd (see https://github.com/korbinian90/ROMEO for options)
parameters.output_dir = 'romeo_tmp'; % if not set pwd() is used
mkdir(parameters.output_dir);

[unwrapped_phase, B0] = ROMEO(double(phs_multi_echo), parameters);
unwrapped_phase(isnan(unwrapped_phase)) = 0;

% Weighted echo averaging
t2s_roi = 0.04; % in [s] unit
W = (TE).*exp(-(TE)/t2s_roi);
weightedSum = 0;
TE_eff = 0;
for echo = 1:size(unwrapped_phase,4)
    weightedSum = weightedSum + W(echo)*unwrapped_phase(:,:,:,echo)./sum(W);
    TE_eff = TE_eff + W(echo)*(TE(echo))./sum(W);
end

field_map = weightedSum/TE_eff*delta_TE.*mask_brain; % Tissue phase in rad
% field_map = -field_map; % If the phase rotation is in the opposite direction

% 2. Complex data fitting + SEGUE
% Complex fitting from MEDI
% [field, error, residual_, phase0]=Fit_ppm_complex_TE(mag_multi_echo.*exp(-1i*phs_multi_echo), TE/1000);
% 
% 
% Inputs.Mask = double(mask_brain); % 3D binary tissue mask, same size as one phase image
% Inputs.Phase = double(field); % For opposite phase
% field_map = SEGUE(Inputs).*mask_brain; % Tissue phase in rad

%% Background field removal
% V-SHARP from STI Suite
smv_size=12;
[local_field, mask_brain_new]=V_SHARP(field_map, mask_brain,'voxelsize',voxel_size,'smvsize',smv_size);
local_field_hz = local_field / (2*pi*delta_TE); % rad to hz

%% QSM
% 1. iLSQR from STI Suite

pad_size = [12, 12, 12];
QSM = QSM_iLSQR(local_field,mask_brain_new,'TE',delta_TE*1e3,'B0',B0_strength,'H',B0_direction,'padsize',pad_size,'voxelsize',voxel_size);
%% χ-separation

% 1. Chi-separation-MEDI
% regularization parameters for chi_separation_MEDI

% params.b0_dir = B0_direction;
% params.CF = CF;
% params.voxel_size = voxel_size;
% params.lambda = 1;
% params.lambda_CSF = 1;
% option_data.qsm = QSM; 
% option_data.mask_CSF = mask_CSF;
% option_data.N_std = N_std;
% [x_para, x_dia, x_tot] = chi_sep_MEDI(mag, local_field_hz, r2prime, N_std, mask_brain_new, params, option_data);


% 2. Chi-separation-iLSQR
% parameters for chi_separation_iLSQR

% params.b0_dir = B0_direction;
% params.CF = CF;
% params.voxel_size = voxel_size;
% option_data.qsm = QSM;
% option_data.N_std = N_std;
% [x_para, x_dia, x_tot] = chi_sep_iLSQR(mag, local_field_hz, r2prime, mask_brain_new, params, option_data);


% 3. chi_sepnet

have_r2prime = exist('r2prime','var');

if have_r2prime
    % Use Chi-sepnet-R2'
    map = r2prime;
else
    % Use Chi-sepnet-R2*
    map = r2star;
end
Dr = 114; % This parameter is different from the original paper (Dr = 137) because the network is trained on COSMOS-reconstructed maps

% resgen = true; % Determine whether to use resolution generalization pipeline or to interpolate to 1 mm isotropic resolution
if all(voxel_size == 1)
    resgen = false;
else
    resgen = true;
end

if resgen
    % Use the resolution generalization pipeline. Resolution of input data is retained in the resulting chi-separation maps
    [x_para, x_dia, x_tot] = chi_sepnet_general_new_wResolGen(chiSepDir, local_field_hz, map, mask_brain_new, Dr, B0_direction, CF, voxel_size, have_r2prime);
else
    % Interpolate the input maps to 1 mm isotropic resolution. Output resolution is also 1 mm isotropic.
    [x_para, x_dia, x_tot] = chi_sepnet_general(chiSepDir, local_field_hz, map, mask_brain_new, Dr, B0_direction, CF, voxel_size, have_r2prime);
end

disp('Writing Files');
if not(isfolder(outdir))
    mkdir(outdir)
end

info = niftiinfo("romeo_tmp/B0.nii");
infoPhase = niftiinfo(phs_path);
infoPhase.Datatype = "single";

niftiwrite(single(x_para), fullfile(outdir, strcat(preString, '_ChiSep-Para.nii.gz')), info, 'Compressed', true);
niftiwrite(single(x_dia), fullfile(outdir, strcat(preString, '_ChiSep-Dia.nii.gz')), info, 'Compressed', true);
niftiwrite(single(x_tot), fullfile(outdir, strcat(preString, '_ChiSep-Total.nii.gz')), info, 'Compressed', true);
niftiwrite(single(QSM), fullfile(outdir, strcat(preString, '_QSM.nii.gz')), info, 'Compressed', true);
niftiwrite(single(local_field), fullfile(outdir, strcat(preString, '_localfield.nii.gz')), info, 'Compressed', true);
niftiwrite(single(unwrapped_phase), fullfile(outdir, strcat(preString, '_unwrappedPhase.nii.gz')), infoPhase, 'Compressed', true);
niftiwrite(single(field_map), fullfile(outdir, strcat(preString, '_fieldMap.nii.gz')), info, 'Compressed', true);
niftiwrite(single(B0), fullfile(outdir, strcat(preString, '_B0.nii.gz')), info, 'Compressed', true);
niftiwrite(single(N_std), fullfile(outdir, strcat(preString, '_N_std.nii.gz')), info, 'Compressed', true);
niftiwrite(single(mask_brain_new), fullfile(outdir, strcat(preString, '_mask_brain_VSHARP.nii.gz')), info, 'Compressed', true);
 
% niftiwrite(x_para, fullfile(outdir, strcat(preString, '_ChiSep-Para.nii.gz')),  'Compressed', true);
% niftiwrite(x_dia, fullfile(outdir, strcat(preString, '_ChiSep-Dia.nii.gz')), 'Compressed', true);
% niftiwrite(x_tot, fullfile(outdir, strcat(preString, '_ChiSep-Total.nii.gz')), 'Compressed', true);
% niftiwrite(QSM, fullfile(outdir, strcat(preString, '_QSM.nii.gz')),  'Compressed', true);
% niftiwrite(local_field, fullfile(outdir, strcat(preString, '_localfield.nii.gz')),  'Compressed', true);
% niftiwrite(unwrapped_phase, fullfile(outdir, strcat(preString, '_unwrappedPhase.nii.gz')), 'Compressed', true);
% niftiwrite(field_map, fullfile(outdir, strcat(preString, '_fieldMap.nii.gz')),  'Compressed', true);
% niftiwrite(B0, fullfile(outdir, strcat(preString, '_B0.nii.gz')),  'Compressed', true);
% niftiwrite(N_std, fullfile(outdir, strcat(preString, '_N_std.nii.gz')),  'Compressed', true);
% niftiwrite(mask_brain_new, fullfile(outdir, strcat(preString, '_BrainMask_eroded1mm.nii.gz')),  'Compressed', true);
disp('job done');


end