import pandas as pd
from dateutil.parser import parse

import plotly.express as px
import textwrap

import definitions.layout_styles as styles


# ===== DATA PROCESSING FUNCTIONS ==============================================================

results_directory = './assets/'

d_raw = pd.read_excel(f'{results_directory}Dev_MPS_papers.xlsx', sheet_name='Read')
# Only include "included" studies
d = d_raw.loc[d_raw.Include == 'Yes']


def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.
        :param string: str, string to check for date
        :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        parse(string, fuzzy=fuzzy)
        return True
    except ValueError:
        return False


def extract_info(prefixes, line, index):
    """ Extract information from bibliography """
    # Date is not always correctly labelled
    if is_date(line):
        bib.loc[index, "Date"] = line[:-1]
        return True

    for prefix in prefixes:
        if line.startswith(prefix):
            bib.loc[index, prefix[:-2]] = line[len(prefix):-1]
            break


# Initialise
n = 1
bib = pd.DataFrame()

# Extract info
with open(f'{results_directory}Step2_AfterAbstractScreening_2024-07-13.txt', 'r') as file:
    for line in file:
        if line.startswith('Reference Type'):
            continue
        if line.startswith('Record Number'):
            # record counter updated for every new record
            n = int(''.join(i for i in line if i.isdigit()))
            bib.loc[n-1, 'Identifier'] = int(n)

        extract_info([s + ': ' for s in ['Author', 'Year', 'Title', 'Journal', 'Abstract', 'Date',
                                         'Short Title', 'DOI', 'URL']], line, n-1)
        # Other fields
        # 'Volume', 'Issue', 'Pages', 'ISSN', 'Accession Number', 'Label', 'Type of Article',
        # 'Notes', 'Author Address', 'Name of Database', 'Language'

# TODO: extract keywords
# bib.set_index('Identifier');

# Correct dates
bib['Date2'] = pd.Series([' '.join([d, y]) if y not in d else d if not d == 'nan' else y for d, y in zip(
    bib.Date.map(str), bib.Year.map(str))])
bib['Date2'] = bib.Date2.apply(lambda date: parse(date).strftime('%Y-%m-%d') if 'nan' not in date else parse(
    '01 01' + date[3:]).strftime('%Y-%m-%d'))

# Check
# pd.options.display.max_columns = 200
# bib[['Date', 'Year', 'Date2']]

# NOTES: some dates are not correct (years do not match)
#        if only year is available set date to 01/01
#        if only month is available set day to 14th

data = pd.merge(d, bib[['Identifier', 'Date2', 'Short Title', 'Abstract', 'URL']],
                how='left', on='Identifier')

# Some other tmp clean-ups:
data.loc[data.Phenotype.str.contains('BAFopathy syndrome: Coffin-Siris'), 'Category'] = 'Syndrome'
data.loc[data.Phenotype.str.contains('Intellectual developmental disorder, X-linked'), 'Category'] = 'Psychiatric'

# Sample size to numeric
data['Sample size'] = pd.to_numeric(data['Sample size'], errors='coerce')  # removed the "- check"
# Dates to dates
data['Date'] = pd.to_datetime(data['Date2'], errors='coerce')

# Combine array info
data['Array'] = [i if i != 'Multiple' else j for i, j in zip(data['Array'], data['Multiple_array'])]

# NOTE: DOI info could be correct in bib in some cases...?

# ================ ##############################


def _sample_size_over_time(data=data, color_by="Category", log_sample_size=True, model_type="ols", scope="overall"):
    # Color set-up
    if color_by in styles.COLOR_MAPS.keys():
        color_map = styles.COLOR_MAPS[color_by]
    else:
        color_map = "Virdis"

    line_color = "grey" if scope == "overall" else None
    model_options = dict(log_y=log_sample_size) if model_type == "ols" else dict(frac=1)

    # Plot
    fig = px.scatter(data, x="Date", y="Sample size", log_y=log_sample_size,
                     color=color_by, color_discrete_map=color_map,
                     hover_name=data.Title.apply(lambda t: "<br>".join(textwrap.wrap(t, width=80))),
                     hover_data="Phenotype",
                     trendline=model_type, trendline_scope=scope, trendline_color_override=line_color,
                     trendline_options=model_options,
                     title="Sample size over time")
    # Make it pretty
    fig.update_traces(marker=dict(size=10, opacity=.5))
    axes_style = dict(mirror=True, ticks="outside", showline=True, linecolor="black", gridcolor="lightgrey")
    ylabel_note = " (log scale)" if log_sample_size else ""
    fig.update_yaxes(title_text=f"<b>Sample size</b>{ylabel_note}", **axes_style)
    fig.update_xaxes(title_text="Publication date", **axes_style)
    fig.update_layout(plot_bgcolor="whitesmoke", width=1300, height=400, margin=dict(l=10, r=10, t=25, b=10))

    return fig
