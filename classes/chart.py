class Chart:
    def __init__(self, title, label, chart_type, labels, data, background_color, border_color, legend="false", display="true"):
        self.title = title
        self.label = label
        self.chart_type = chart_type
        self.labels = labels
        self.data = data
        self.background_color = background_color
        self.border_color = background_color
        self.legend = "true" if self.chart_type == "pie" else "false"
        self.display = "false" if self.chart_type == "pie" else "true"
