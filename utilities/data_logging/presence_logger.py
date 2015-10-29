
import data_logger_base

class Presence_Logger(data_logger_base.Data_Logger):
    def __init__(self, log_directory, archive_prefix, data_item_names):
        self.data_item_names = data_item_names
        data_logger_base.Data_Logger.__init__(self, log_directory, archive_prefix)
        
    def get_google_timeline_javascript(self, title, item_name, div_id, chart_options=None):
        
        jscript = ""
        if self.isInitialized():
            
            # Get the most recent data set (all the data from today)
            dataset = self.get_data_set()
            if dataset == None or len( dataset ) == 0:
                return "// None available"
            
            
            options = "{ title: '%s'%s }" % (title, "%s")
            if isinstance( chart_options, str):
                options = options % (", "+chart_options)
            elif isinstance( chart_options, list):
                options = options % (", " + ",".join(chart_options) )
            else:
                options = options % ""
            
            # Build the return string
            return_string = """
    
            var dataTable = new google.visualization.DataTable();
    
            dataTable.addColumn({ type: 'string', id: '%s' });
            dataTable.addColumn({ type: 'date', id: 'Start' });
            dataTable.addColumn({ type: 'date', id: 'End' });
    
            dataTable.addRows([
              
            %s             //   TIMELINE DATA
    
            ]);
    
            chart = new google.visualization.Timeline(document.getElementById('%s'));
            chart.draw(dataTable);
            
            """ % (item_name, "%s", div_id)
            
            
            # Initialize the state dictionaries
            start_times = {}
            last_present_times = {}
            for item in self.data_item_names:
                start_times[item] = None
                last_present_times[item] = None
            
            # Go through the data and write out a string whenever the item
            # is no longer present.
            return_string_data = ""
            
            for row in dataset:
                row_time = row['time_str']
                row_data = row['data']
                
                for item in self.data_item_names:
                    # Item is present
                    if item in row_data:
                        if start_times[item] == None:  # No start time yet, add it
                            start_times[item] = row_time
                        last_present_times[item] = row_time
                            
                    # Item is not present
                    else:
                        if start_times[item] != None:  # Has start time, add end time
                            # write a string
                            return_string_data += ("['%s',  %s, %s],\n" % (item, start_times[item], last_present_times[item]))
                            # reset start time
                            start_times[item] = None
                            last_present_times[item] = None
            
            # Make sure any items currently present get closed properly
            for item in self.data_item_names:
                if start_times[item] != None:
                    return_string_data += ("['%s',  %s, %s],\n" % (item, start_times[item], last_present_times[item]))
                    
            # Remove the trailing comma and return line    
            if return_string_data.endswith(",\n"):
                return_string_data = return_string_data[:-2]
            
            jscript = return_string % return_string_data
            
        return jscript
