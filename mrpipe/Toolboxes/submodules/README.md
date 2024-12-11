#Comments to submodules:

### Add new Submodule:

example:

```
cd /path/to/location
git submodule add https://github.com/spm/spm.git spm12

```
so the structure will be:

`git submodule add #address #destinationDirectory`

destination directory can be relative from your current position.


### checkout specific branch of a submodule:

https://stackoverflow.com/questions/1777854/how-can-i-specify-a-branch-tag-when-adding-a-git-submodule

```
cd submodule_directory
git checkout v1.0
cd ..
git add submodule_directory
git commit -m "moved submodule to v1.0"
git push

```