# Database commands

#### login
	mongo internal-mongo-elb-624130134.us-east-1.elb.amazonaws.com:27017
	use metricdb
	db.auth("analyzer","hyperpilot")
	show collections

#### Show keys of all documents.   
	db.calibration.find().forEach(function(doc){print(Object.keys(doc));});
	
#### Rename subdocuments in a document.

~~~
var query={"testResult.qosMetric": {$exists: true}};

db.calibration.find(query).snapshot().forEach(function(item)
{
    print(item);
    for(i=0; i != item.testResult.length; ++i)
    {
        item.testResult[i].qosValue=item.testResult[i].qosMetric;
        delete item.testResult[i].qosMetric

    }
    db.calibration.update({_id: item._id}, item);
});
~~~