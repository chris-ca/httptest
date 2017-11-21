# httptest
Batch test URLs against status codes

# Installation
- Pull and rename *.py-dist to *.py
- Create a file with URLs to check

### Example
Read URLs from file accommodations.txt, setting cookies for PROD environments and validating against template "details"
```./httptest.py --env prod --file accommodations.txt  --template details```

### Output
Output is made to `stdout` and appended to `./httptest.log`
