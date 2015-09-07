
import csv
import datetime

def convert_file_to_timeline_string(data_filename, mutex, search_items, days=1, seconds=0):
    
    # start_time is "now" minus days and seconds
    # only this much data willl be shown
    start_time = datetime.datetime.now() - datetime.timedelta(days,seconds)
    
    # Load the data from the file
    mutex.acquire()
    file_handle = open(data_filename, 'r')
    csvreader = csv.reader(file_handle)
    lines = 0
    userdata = []
    for row in csvreader:
        userdata.append(row)
        lines += 1
    mutex.release()
    
    # Build the return string
    return_string = ""
    
    # Skip the ones before the start_time
    start_index = len(userdata)
    for i, row in enumerate(userdata):
        dt = datetime.datetime.fromtimestamp(float(row[0]))
        if dt > start_time:
            start_index = i
            break
    
    # Process the remaining data into a usable structure
    processed_data = []
    for i, row in enumerate(userdata[start_index:]):
        
        dt = datetime.datetime.fromtimestamp(float(row[0]))
        
        year   = dt.strftime('%Y')
        month  = str(int(dt.strftime('%m')) - 1) # javascript expects month in 0-11, strftime gives 1-12 
        day    = dt.strftime('%d')
        hour   = dt.strftime('%H')
        minute = dt.strftime('%M')
        second = dt.strftime('%S')
        
        time = 'new Date(%s,%s,%s,%s,%s,%s)' % (year,month,day,hour,minute,second)
        
        temp = {}
        temp["time"] = time
        for item in search_items:
            if item in row:
                temp[item] = "1"
        
        processed_data.append( temp )
    
    if len(processed_data) == 0:
        return "[] // None available"
    
    # Save the first state
    start_times = {} 
    for item in search_items:
        if item in processed_data[0]:
            start_times[item] = processed_data[0]["time"]
        else:
            start_times[item] = None
    
    # Go through the processed data and write out a string whenever the user
    # is no longer present.
    for i, row in enumerate(processed_data[1:]):
        for item in search_items:
            if start_times[item] == None and (item in row):
                start_times[item] = processed_data[i]["time"]
            if start_times[item] != None and (not (item in row)):
                # write a string
                return_string += ("['%s',  %s, %s],\n" % (item,  \
                                                          start_times[item],  \
                                                          row["time"]))
                # set start time to None
                start_times[item] = None
    
    for item in search_items:
        if start_times[item] != None:
            return_string += ("['%s',  %s, %s],\n" % (item,  \
                                                      start_times[item],  \
                                                      processed_data[-1]["time"]))
    # Remove the trailing comma and return line    
    if len(return_string) > 2:
        return_string = return_string[:-2]
    
    return return_string

