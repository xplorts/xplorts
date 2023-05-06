# xplorts - Explore time series datasets

`xplorts` ("explore-ts") is a collection of Python tools to make standalone HTML documents
containing interactive charts.  It is particularly aimed at showing time series data (hence
the "ts") with annual, quarterly or monthly periodicity, such as that published
by national statistical institutes by way of national accounts, productivity, or labour
markets series.

Once created, the HTML documents can be used with any web browser.  They do not need an
active internet connection.

## Installation
```
pip install xplorts
```

## Demo
[Explore UK output per hour worked](docs/xplor_lprod%20oph%20annual%20by%20section.html)

### Make explorer for ONS labour productivity data

1. Download [Output per hour worked, UK](https://www.ons.gov.uk/economy/economicoutputandproductivity/productivitymeasures/datasets/outputperhourworkeduk) from the ONS web site.

2. Extract productivity, gross value added and labour data using the utility script `ukons_lprod_to_csv.py`.
```
python xplorts/utils/ukons_lprod_to_csv.py outputperhourworked.xlsx --quarterly --section
```
Note: For older versions of Pandas you will have to open the Excel file, save it as `.xls`, and use that rather than the original `.xlsx` format.

3. Run the script `xplor_lprod` to create a stand-alone `HTML` labour productivity explorer.
```
python xplorts/xplor_lprod.py outputperhourworked.csv -d date -b industry -p lprod -g gva -l labour
```

4. Use the explorer file `outputperhourworked.html` in any web browser.


## Documentation



### Using xplorts on the command line
- Install (once, possibly within a particular virtual environment)
- Open command line window (shell)
- Activate virtual environment?
    On Windows:
    ```activate python36_plus_hv2```
    On Mac:
    ```conda activate python36_plus_hv2```
- Run command


---
### Developer note
This document uses
[Github-flavored Markdown](https://guides.github.com/features/mastering-markdown/)
.
