 update backend_appendices set tag='P' where tag=2 and appendix_category_id = 4;
 update backend_appendices set tag='D' where tag=1 and appendix_category_id = 4;

 update backend_appendices set tag=CONCAT(tag,',','sample_quality') where appendix_category_id = 4 and code in (1,2,4,6,7,8,10,11,13,14,21,22,23,24,25,33,34,41);
 update backend_appendices set tag=CONCAT(tag,',','data_quality') where appendix_category_id = 4 and code in (3,5,12,17,18,19,20,28,29,30,31,32,35,36,37,39,42,43);
 update backend_appendices set tag=CONCAT(tag,',','eligibility') where appendix_category_id = 4 and code in (9,15,16,26,27,38,40,44)


/*sample quality - 1,2,4,6,7,8,10,11,13,14,21,22,23,24,25,33,34,41,
data quality - 3,5,12,17,18,19,20,28,29,30,31,32,35,36,37,39,42,43,
eligibility - 9,15,16,26,27,38,40,44
1	Specimen sent to CPHL Laboratory was  less than 0.75ml
2	Specimen sent to CPHL was haemolysed
3	Mismatching Specimen identifiers on request form and sample
4	Well labeled DBS card without any blood spots
5	Blood spots were collected onto a dirty/soiled DBS card,compromising the specimen integrity
6	Sample not recieved at CPHL Lab(only the request form was recieved at the testing Lab)
7	All Dry Blood Spots on the card were less than the required size i.e not filling the perforated area
8	DBS sample sent on wrong Card
9	Patient has been on ARVs for less than 6 months(doesn't qualify for Viral Load testing as per Algorithm)
10	Dry Blood sample sent with less than 2 spots
11	DBS Sample older than 3 weeks,VL test can't be done on DBS older than 3 weeks.
12	Mismatching ART number between sample and form
13	Well labeled cryo viral container without any sample in it was sent to CPHL Lab
14	Sample not recieved at CPHL Lab(only the request form was recieved at the testing Lab)
15	Patient has been on ARVs for less than 6 months(doesn't qualify for Viral Load testing as per Algorithm)
16	Patient had viral load results above 1000cp/ml in less than 6 months ago (Refer to testing Algorithm)
17	Patient has wrong date of treatment initiation i.e date earlier than ART role out
18	Patient has wrong date of treatment initiation i.e date earlier than ART role out
19	Patient's date of treatment initiation not included on the form thus failed to determine VL testing eligibility
20	Patient's date of treatment initiation not included on the form thus failed to determine VL testing eligibility
21	Sample was sent in wrong container thus compromising the sample integrity
22	Wrong sample type was sent to CPHL-Laboratories,Only Plasma and Dried Blood Spots(DBS) are required
23	DBS sample was sent on non-perforated card(not able to get the right spot size during sample processing)
24	DBS sample was wet and or had moulds thus compromising with the sample integrity
25	Sample was sent in a damaged container
26	Patient has not yet been initiated on ART(doesn't qualify for Viral Load testing as per Algorithm)
27	Patient has not yet been initiated on ART(doesn't qualify for Viral Load testing as per Algorithm)
28	Patient's dispatch form sent without patient's identifications(ART number or Other number)
29	Patient's dispatch form sent without patient's identification(ART number or Other number)
30	Two forms were sent for the same sample(only dispatched results for one form)
31	Two forms were sent for the same sample(only dispatched results for one form)
32	Recieved an empty DBS card
33	Sample was delivered under wrong storage container thus compromising the sample integrity
34	DBS card with presence of serum rings i.e improper drying(affecting the specimen integrity)
35	DBS Card without ART and form number details(DBS card cannot be linked to request form)
36	Patient has wrong date of treatment initiation i.e date is beyond the current calender date.
37	Patient has wrong date of treatment initiation i.e date is beyond the current calendar date
38	Patient had viral load results less than 1000cp/ml or Not Detected in less than 12 months ago.Refer to testing algorithm.
39	Plasma sample container without ART and form number details (sample cannot be linked to request form)
40	Patient had viral load results less than 1000cp/ml or Not Detected in less than 12 months ago.Refer to testing algorithm.
41	Wrong sample type sent to CPHL-Laboratories,Only Plasma and Dried Blood Spots(DBS) are required
42	ART Number details are shared by different patients from the same facility.
43	ART Number details are shared by different patients from the same facility.
44	Patient had viral load results above 1000cp/ml in less than 6 months ago (Refer to testing Algorithm)
*/