import os
import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

from dash import Dash, html, dcc, callback, Output, Input, dash_table
import dash_bootstrap_components as dbc

port = int(os.environ.get("PORT", 5000))

app = Dash(__name__)


data_path = 'data/maverick_data_processed.csv'
df = pd.read_csv(data_path)
df = df.drop(columns=['Unnamed: 0'])

dedupe_cols = ['condition', 'model_year', 'make',
               'model', 'trim_level', 'list_price',
               'exterior_color', 'interior_color',
                'hybrid_or_eco', 'mileage', 'dealer_address']


def generate_mean_and_trend(df):
    # OLS for plotting 
    mean_price = df.groupby(by='date_parsed').mean(numeric_only=True)['list_price'].round(0).astype(int)
    mean_price = mean_price.to_frame().reset_index().rename(columns={'list_price':'mean_list_price'})

    # generate a trendline for mean_price
    mean_price['date_parsed'] = pd.to_datetime(mean_price['date_parsed'])
    mean_price['date_parsed_float'] = mean_price['date_parsed'].apply(lambda x: datetime.datetime.timestamp(x)) 
    mean_price['mean_list_price'] = mean_price.mean_list_price.astype(float)

    # Training Data
    X = mean_price.loc[:,['date_parsed_float']] # features
    y = mean_price.loc[:,['mean_list_price']] # target

    # train the model
    model = LinearRegression()
    model.fit(X,y)

    # store the fitted values as a time series with the same index as
    # the training data
    #y_pred = pd.Series(model.predict(X), index=X.index)
    predictions = model.predict(X)
    trend_line = []
    for i in range(len(predictions)):
        trend_line.append(predictions[i][0])
    mean_price['trend_line'] = trend_line
    return mean_price

mean_price = generate_mean_and_trend(df)

def generate_dailybar(df):
    grouped = df.groupby(by='date_parsed').count()['model_year'].to_frame().rename(columns={'model_year':'count'}).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=grouped['date_parsed'],
        y=grouped['count'],
        text=grouped['count'],
        textposition='auto'
    ))
    fig.update_layout(
        title={'text':'Number of Mavericks Available Over Time'},
        yaxis_title={'text':'Count'}
    )
    return fig

daily_bar = generate_dailybar(df)


def plot_mean_price_over_time(df):
    # generate df of data.  No callback required for this plot unless you want to try filtering by trim level

    t = mean_price['date_parsed']
    y = mean_price['mean_list_price']
    y_trend = mean_price['trend_line']

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=y, mode='markers', name='Price (USD)'))
    fig.add_trace(go.Scatter(x=t, y=y_trend, mode='lines', name='Trend'))
    fig.update_layout(
            title={'text':'Average Price for All Trim Levels Over Time'},
            xaxis_title={'text':'Date Data Parsed'},
            yaxis_title={'text':'Average Price'}
        )
    return fig

mean_price_figure = plot_mean_price_over_time(mean_price)


app.layout = dbc.Container([

    dbc.Row([
        dbc.Col(
            html.Div([
            html.H4('Box and Whisker Price', style={"text-align":"center"}),
            dcc.Graph(id='graph-content_bw'),
            html.H6('Select a date for box and whisker: '),
            dcc.Dropdown(df.date_parsed.unique(), id='date-dropdown'),            
            ]),
        width=4),

        dbc.Col(
            html.Div([
            html.H4('Number Available', style={"text-align":"center"}),
            dcc.Graph(
                id='daily_bar_graph',
                figure=daily_bar),
            ]),
        width=4),

        dbc.Col(
            html.Div([
            html.H4('Avg Price and Trend (WIP)', style={"text-align":"center"}),
            dcc.Graph(
                id='trendline',
                figure=mean_price_figure
            )
            ]),
        width=4)
    ]),

    dbc.Row([
        dbc.Col(
            html.Div([
            html.H6('Data Scraped from Cars.com', style={"text-align":"center"}),
            ]),)
    ], 
    justify='left'),

    dbc.Row([
        dbc.Col(
            html.Div([
                dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns],
                                     filter_action='native'),
            ])
        )
    ]),
], 
fluid=True)


# generate box and whisker plot
@callback(
    Output('graph-content_bw','figure'),
    Input('date-dropdown', 'value')
)
def box_and_whisker(date):
    acceptable_trim_levels = ['XL','XLT','LARIAT']
    single_date_data = df[df.date_parsed == date]
    num_cars = len(single_date_data)
    figure = px.box(single_date_data, x='trim_level', y='list_price', points='all', 
            title=f'Used Ford Maverick Prices Listed on Cars.com. {num_cars} cars shown', 
            category_orders={'trim_level':acceptable_trim_levels},
            labels={'trim_level':'Trim Level','list_price':'List Price'})
    return figure



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=port, )

