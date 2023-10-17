Generates a single webpage rendering all module views from all given antiSMASH results.
The webpage reuses slightly tweaked antiSMASH javascript and CSS to replicate antiSMASH's visualisation.

# Installation
Make sure python3 is available.

Clone the repository somewhere accessible (or download the archive and extract it). 

# Use
The script takes two arguments:
- an input directory, which should contain subdirectories with antiSMASH results (or at least `regions.js` and the results JSON)
- an output directory, which doesn't need to exist, but any existing files will be overwritten

`<path you copied to>/gather_modules.py input_dir output_dir`


# Output
There will now be an `index.html` in the given output directory, which looks like the following:
![image](https://github.com/SJShaw/module_gatherer/assets/1700735/bb712254-6fbd-439b-aebe-9f1e115ac3d5)
