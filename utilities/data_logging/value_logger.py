
import data_logger_base

class Value_Logger(data_logger_base.Data_Logger):
    def __init__(self, log_directory, archive_prefix, value_names):
        
        if isinstance(value_names, list):
            self.value_names = value_names
        elif isinstance(value_names, str):
            self.value_names = [value_names]
        else:
            print "Value_Logger: Unsupported input type: " + str( type(value_names) )
            return
            
        data_logger_base.Data_Logger.__init__(self, log_directory, archive_prefix)
    
    def get_google_linechart_javascript(self, title, div_id, chart_options=None):
        jscript = ""
        if self.isInitialized():
            
            legend = []
            for name in self.value_names:
                legend.append("'"+name+"'")
            
            if len( legend ) > 1:
                legend_str = ",".join(legend)
            else:
                legend_str = legend[0]
            
            
            options = "{ title: '%s'%s }" % (title, "%s")
            if isinstance( chart_options, str):
                options = options % (", "+chart_options)
            elif isinstance( chart_options, list):
                options = options % (", " + ",".join(chart_options) )
            else:
                options = options % ""
            
            jscript = """
                
                var rows = data.split('\\n');
                
                var result = [['Time', %s ]];
                
                for ( var i = 0; i < rows.length; i++)
                {
                    var row = rows[i];
                    var items = row.split(",");
                    if (items.length != %d)
                        continue;
                    
                    var time = items[0];
                    var d = new Date(0); // The 0 there is the key, which sets the date to the epoch
                    d.setUTCSeconds(parseInt(time));
                    
                    data = [d]
                    for ( var j = 1; j < items.length; j++)
                    {
                        t = parseFloat( items[j] );
                        if (t == NaN)
                        {
                            t = null;
                        }
                        data.push( t );
                    }
                    
                    result.push( data );
                }
                
                var data = google.visualization.arrayToDataTable(result);
                var options = %s;
                var chart = new google.visualization.LineChart(document.getElementById('%s'));
                chart.draw(data, options);
                
                """ % ( legend_str, len(self.value_names)+1, options, div_id )
        
        return jscript
    