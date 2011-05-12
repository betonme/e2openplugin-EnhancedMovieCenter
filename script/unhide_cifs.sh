find $EMC_HOME -name cifs* | grep -v '.ts' | while read fn; do mv $fn $fn.ts; done
