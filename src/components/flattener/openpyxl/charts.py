"""
Chart extraction from Excel workbooks.

Extracts chart definitions, series, axes, and styling information.
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.chart import (
    BarChart, LineChart, PieChart, AreaChart,
    ScatterChart, BubbleChart, RadarChart
)

logger = logging.getLogger(__name__)


def extract_charts(wb: Workbook) -> List[Dict[str, Any]]:
    """
    Extract all charts from workbook.

    Args:
        wb: Openpyxl workbook object

    Returns:
        List of chart dictionaries
    """
    logger.debug("Extracting charts from workbook...")

    charts = []

    for ws in wb.worksheets:
        sheet_charts = _extract_sheet_charts(ws)
        charts.extend(sheet_charts)

    logger.info(f"✓ Extracted {len(charts)} charts")
    return charts


def _extract_sheet_charts(ws: Worksheet) -> List[Dict[str, Any]]:
    """
    Extract charts from a single worksheet.

    Args:
        ws: Worksheet object

    Returns:
        List of chart dictionaries
    """
    charts = []

    if not hasattr(ws, '_charts') or not ws._charts:
        return charts

    for idx, chart in enumerate(ws._charts, start=1):
        try:
            chart_info = {
                'sheet': ws.title,
                'index': idx,
                'type': _get_chart_type(chart),
                'title': _get_chart_title(chart),
                'anchor': _get_chart_anchor(chart),
                'series_count': len(chart.series) if hasattr(chart, 'series') else 0,
                'series': [],
                'axes': {}
            }

            # Extract series information
            if hasattr(chart, 'series') and chart.series:
                for series_idx, series in enumerate(chart.series, start=1):
                    series_info = _extract_series(series, series_idx)
                    if series_info:
                        chart_info['series'].append(series_info)

            # Extract axes information
            chart_info['axes'] = _extract_axes(chart)

            # Chart style
            if hasattr(chart, 'style') and chart.style:
                chart_info['style'] = chart.style

            # Legend
            if hasattr(chart, 'legend') and chart.legend:
                chart_info['legend'] = {
                    'position': chart.legend.position if hasattr(chart.legend, 'position') else None
                }

            charts.append(chart_info)
            logger.debug(f"Extracted chart {idx} from {ws.title}")

        except Exception as e:
            logger.warning(f"Error extracting chart {idx} from {ws.title}: {e}")

    return charts


def _get_chart_type(chart) -> str:
    """Get chart type as string."""
    chart_type_map = {
        BarChart: 'bar',
        LineChart: 'line',
        PieChart: 'pie',
        AreaChart: 'area',
        ScatterChart: 'scatter',
        BubbleChart: 'bubble',
        RadarChart: 'radar'
    }

    for chart_class, type_name in chart_type_map.items():
        if isinstance(chart, chart_class):
            return type_name

    return type(chart).__name__


def _get_chart_title(chart) -> Optional[str]:
    """Extract chart title."""
    try:
        if hasattr(chart, 'title') and chart.title:
            if hasattr(chart.title, 'text') and chart.title.text:
                # Handle RichText
                if hasattr(chart.title.text, 'rich'):
                    rich = chart.title.text.rich
                    if hasattr(rich, 'paragraphs') and rich.paragraphs:
                        # Extract text from paragraphs
                        texts = []
                        for para in rich.paragraphs:
                            if hasattr(para, 'r'):
                                for run in para.r:
                                    if hasattr(run, 't'):
                                        texts.append(run.t)
                        return ' '.join(texts) if texts else None
                # Handle plain text
                return str(chart.title.text)
    except Exception as e:
        logger.debug(f"Error extracting chart title: {e}")

    return None


def _get_chart_anchor(chart) -> Optional[str]:
    """Extract chart anchor position."""
    try:
        if hasattr(chart, 'anchor'):
            anchor = chart.anchor
            if hasattr(anchor, '_from') and anchor._from:
                col = anchor._from.col
                row = anchor._from.row
                return f"{col},{row}"
    except Exception as e:
        logger.debug(f"Error extracting chart anchor: {e}")

    return None


def _extract_series(series, index: int) -> Optional[Dict[str, Any]]:
    """Extract series information."""
    try:
        series_info = {
            'index': index,
            'title': None,
            'values': None,
            'categories': None
        }

        # Series title
        if hasattr(series, 'title') and series.title:
            series_info['title'] = str(series.title)

        # Series values reference
        if hasattr(series, 'val') and series.val:
            series_info['values'] = str(series.val)

        # Series categories reference
        if hasattr(series, 'cat') and series.cat:
            series_info['categories'] = str(series.cat)

        return series_info

    except Exception as e:
        logger.debug(f"Error extracting series {index}: {e}")
        return None


def _extract_axes(chart) -> Dict[str, Any]:
    """Extract axes information."""
    axes_info = {}

    try:
        # X axis
        if hasattr(chart, 'x_axis') and chart.x_axis:
            x_axis = chart.x_axis
            axes_info['x_axis'] = {
                'title': str(x_axis.title) if hasattr(x_axis, 'title') and x_axis.title else None,
                'type': type(x_axis).__name__
            }

        # Y axis
        if hasattr(chart, 'y_axis') and chart.y_axis:
            y_axis = chart.y_axis
            axes_info['y_axis'] = {
                'title': str(y_axis.title) if hasattr(y_axis, 'title') and y_axis.title else None,
                'type': type(y_axis).__name__
            }

    except Exception as e:
        logger.debug(f"Error extracting axes: {e}")

    return axes_info


def write_charts_file(charts: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Write charts information to text file.

    Format:
    Chart 1:
      Sheet: Sheet1
      Type: line
      Title: Sales Over Time
      Position: 5,2
      Series Count: 2
      Series:
        1. Title: Q1 Sales
           Values: Sheet1!$B$2:$B$10
           Categories: Sheet1!$A$2:$A$10
        2. Title: Q2 Sales
           Values: Sheet1!$C$2:$C$10
      Axes:
        X Axis:
          Title: Month
          Type: DateAxis
        Y Axis:
          Title: Revenue
          Type: NumericAxis

    Args:
        charts: List of chart dictionaries
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# Charts\n')
        f.write('# ' + '=' * 50 + '\n\n')

        if not charts:
            f.write('(No charts found)\n')
            return

        for chart in charts:
            f.write(f"Chart {chart['index']}:\n")
            f.write(f"  Sheet: {chart['sheet']}\n")
            f.write(f"  Type: {chart['type']}\n")

            if chart['title']:
                f.write(f"  Title: {chart['title']}\n")

            if chart['anchor']:
                f.write(f"  Position: {chart['anchor']}\n")

            f.write(f"  Series Count: {chart['series_count']}\n")

            if chart['series']:
                f.write('  Series:\n')
                for series in chart['series']:
                    f.write(f"    {series['index']}. ")
                    if series['title']:
                        f.write(f"Title: {series['title']}\n")
                    else:
                        f.write('(No title)\n')

                    if series['values']:
                        f.write(f"       Values: {series['values']}\n")
                    if series['categories']:
                        f.write(f"       Categories: {series['categories']}\n")

            if chart['axes']:
                f.write('  Axes:\n')
                if 'x_axis' in chart['axes']:
                    x_axis = chart['axes']['x_axis']
                    f.write('    X Axis:\n')
                    if x_axis['title']:
                        f.write(f"      Title: {x_axis['title']}\n")
                    f.write(f"      Type: {x_axis['type']}\n")

                if 'y_axis' in chart['axes']:
                    y_axis = chart['axes']['y_axis']
                    f.write('    Y Axis:\n')
                    if y_axis['title']:
                        f.write(f"      Title: {y_axis['title']}\n")
                    f.write(f"      Type: {y_axis['type']}\n")

            if 'legend' in chart and chart['legend']:
                legend = chart['legend']
                if legend['position']:
                    f.write(f"  Legend: {legend['position']}\n")

            if 'style' in chart:
                f.write(f"  Style: {chart['style']}\n")

            f.write('\n')

    logger.debug(f"Wrote charts to: {output_path}")
