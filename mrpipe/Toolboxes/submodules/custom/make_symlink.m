function make_symlink(target, link)
    target = char(java.io.File(target).getCanonicalPath());  % absolute path
    if ispc
        cmd = sprintf('mklink "%s" "%s"', link, target);
    else
        cmd = sprintf('ln -sf "%s" "%s"', target, link);
    end
    [status, msg] = system(cmd);
    if status ~= 0
        error('make_symlink:failed', '%s', msg);
    end
end