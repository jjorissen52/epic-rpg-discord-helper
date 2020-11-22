Use this command (with `imagemagick` installed) to make png versions of `.ico` files in the working directory:

```bash
#            V select only the first ico resolution, which is the largest
#                                 V set the filename: variable to be the name of the input file without an extension
#                                       V treat the selected ico as a 64x64
#                                                       V output file name based on input file name
convert *.ico[0] -set filename: "%[t]" -thumbnail 64x64 "%[filename:].png
```
