import pyexcel
from pyexcel.ext import xlsx
from pyexcel.ext import xls
import os
import scipy.optimize as opt 
import numpy as np

#Take in global background content from csv files - fe & strategy
with open(os.path.join('fe.csv'), 'r') as f:
        FE_data = f.readlines()
        
#take in the strategy for each of the 3 companies for 2016 & 2017.
with open(os.path.join('strategy.csv'), 'r') as f:
        Strategy_data = f.readlines()

for i in range(len(FE_data)):
    FE_data[i] = FE_data[i].replace('\n','').replace('\r','').split(',')
for i in range(len(Strategy_data)):
    Strategy_data[i] = Strategy_data[i].replace('\n','').replace('\r','').split(',')

#book now contains the entire excel workbook      
book = pyexcel.get_book(file_name="CarDetails.xlsx")
startYear = 2015
n=100000
totalPrefs = np.zeros((n,3,3,4))

def createPrefs():
    #print 'In createPrefs'
    brandPrefs = np.random.dirichlet((1,1,1),n)
    techPrefs = np.random.dirichlet((1,1,2,2),n)
    eachCompanyPrefs = brandPrefs[...,None]+techPrefs[:,None]
    OEMPrefs = np.random.dirichlet((4,3,3),n)
    global totalPrefs
    totalPrefs = OEMPrefs[...,None,None]+eachCompanyPrefs[:,None]     

createPrefs()

def demand(thisPrice):
    #print "In demand"
    allPrefs = totalPrefs/thisPrice
    flattened = allPrefs.reshape(n,-1)
    maximum = flattened.argmax(axis=1)
    bins = np.bincount(maximum,minlength=36)
    bins = bins.reshape((3,3,4))
    #print bins
    return bins
    
price = [[],[],[]]
for key,value in book.sheets.items():
    value.delete_rows([0])
    choices = []
    #choices contains all the choices that are offered
    for row in value:
        price[int(row[6])%startYear].append(int(row[8]))
        if(row[4]) in choices:
            continue
        else:
            choices.append(row[4])

#create a 3x3x4 size price matrix having the prices of all the OEMs 
p = np.array(price)
a = np.zeros((3,3,3,4))
count = 0;
for prices in p:
    a[count] = prices.reshape((3,3,4))
    count = count + 1
 
prices = a
del a,p,price   

#for each year 2016 & 2017
strategy_headings = np.array(Strategy_data)[0]
strategy = np.delete(np.array(Strategy_data),0,0)
for i in strategy:
    year = int(i[0])
    Stgy = {'Ford':i[1].split('&'), 'GM': i[2].split('&'),'Toyota':i[3].split('&')}    
  
    allTargets = []
    #for each OEM  
    for key,value in book.sheets.items():
        if key=='Ford':
            oem = 0
        elif key=='GM':
            oem = 1
        else:
            oem = 2
        
        #value.delete_rows([0])
        target = []
        count = -1
        for row in value:
            count +=1;
            #for each of the options that satisfy its strategy
            if (int(row[6]) == int(year)) and (row[4] in Stgy[key]):
                prices_lastyear = prices[(year-1)%startYear]
                prices_updated = prices_lastyear
                prices_updated[oem,(count%12)/4,count%4] = float(row[8])
                #print '****'                
                #print 'done', key, row[4], int(i[0]), row[7], count
                
                q = demand(prices_updated)    
                row.append(q[oem,(count%12)/4,count%4])
                target.append(row)
        
        #print '\n\n*&*&*&*&'
        #print target
        allTargets.append(target)
        #print '\n**End of sheet : ' + key
        
        
        #now for this OEM I have all my target rows, that need to be optimized
        
        #run the optimization algorithm
        #using qis as upper bound
        #constraint of sigma qi.ei >= C* sigma qi
        #maximise qi*(pi-ci)
        bnds = ()
        C = []
        arow=[]
        bnumerator = 0
        bdenom = 0
        for config in target:
            #length = len(config) 
            C.append((config[8]-config[7])*-1)
            bound = (0,config[11])
            bnds = bnds + (bound,)
            arow.append(1)
            bnumerator += config[11] * config[10]
            bdenom +=config[10]
        
        A = []
        A.append(arow)
        B = []
        B.append(bnumerator/bdenom)
        
        #C has to have all the profit values that are to MAX for each quantity
        #A's first row has to have the coefficients of sigma qi = 1         
        #B has the value of (sigma(qi * ei)/sigma(qi))
        #bounds are the respective bounds of quantity obtained from the demand function
        
        #maximise
        res = opt.linprog(C, A_ub=A, b_ub=B, bounds = bnds, options={"disp": True})
        
    print '\n**End of Year : ' + str(year)
    print ' ^%^%^%^%^%^%^%^%^%^%^%'
    print 'NEED TO CHECK DEMAND against Sales'
       
    for key,value in book.sheets.items():
        if key=='Ford':
            oem = 0
        elif key=='GM':
            oem = 1
        else:
            oem = 2
        
        target = []
        count = -1
        for row in value:
            count +=1;
            #for each of the options that satisfy its strategy
            if (int(row[6]) == int(year)) and (row[4] in Stgy[key]):
                prices_thisyear = prices[year%startYear]
                prices_updated = prices_thisyear
                prices_updated[oem,(count%12)/4,count%4] = float(row[8])
                #print '****'                
                #print 'done', key, row[4], int(i[0]), row[7], count
                
                q = demand(prices_updated)    
                row.append(q[oem,(count%12)/4,count%4])
                target.append(row)
                
        #compare with the each of allTargets[oem]'s values
        print '\n\nExpected Demand vs Actual Demand for '
        countTarget = 0
        for rows in allTargets[oem]:
             print 'OEM : '+ str(key)+' Vehicle : '+str(rows[3])+' TechChoice : '+str(rows[4])
             print str(rows[11])+' vs. '+str(target[countTarget][11])
             countTarget+=1
            
                
       

    #for each of the options that satisfy its strategy 
        #run the demand function with this option & last years pi, & get the value of qi

    #now we have the value of q for each of the rows that follows strategy for OEM(i)

    #run the optimization algorithm
        #using qis as upper bound
        #constraint of sigma qi.ei >= C* sigma qi
        #maximise qi*(pi-ci)

    #now we have actual values of each qi for OEM1

#after doing for all 3 OEMs

#for each book's that year
    #for each of the options that satisfy the strategy
        #run the demand function with this option & new pis, & get the value of qi

    #for each of these qi, compare with calculated qi, and give the excess or lesser values produced, and the potential loss/gain
        
    #for the both permutation 
#    targetRows_both = []
#    targetRows_gas = []
#    targetRows_hev = []
#    FE = []
#    Gas = []
#    target = []
#    
#    for row in value:
##        print 'ROW[6]' 
##        print row[6], type(row[6]), int(row[6]), type(int(row[6]))
##        print 'year'
##        print year, type(year), int(year), type(int(year))
#        if int(row[6]) == int(year):
#            targetRows_both.append(row)
#            targetRows_gas.append(row) if row[4].lower() == "gas" else targetRows_hev.append(row)             
##            if row[4].lower() == "gas":
##                targetRows_gas.append(row)
##            else:
##                targetRows_hev.append(row) 
#                       
#    
#    #appending into FE the 'year's' data                       
#    for row in FE_data:
#        if(str(row[0])==year):
#            FE.append(row)
#    
#    #appending into Gas the 'year's' data      
#    for row in Gas_data: 
#        if(str(row[0])==year):
#            Gas.append(row)
#    
#    target.append(targetRows_both)
#    target.append(targetRows_gas)
#    target.append(targetRows_hev)
#    
#    for config in target:
#        length = len(config)
#        print length       
#        C = []
#        A = []
#        B = []
#        arow_1 = []
#        arow_2 = []
#        #C has to have all the profit values that are to MAX
#        #A's first row has to have the coefficients of CAFE = 1 eqn
#        #A's second row has to have coefficients of number of cars = 1
#        #B has to have the value for CAFE & number of cars
#        for row in config:
#            C.append(row[7]*-1)
#            arow_1.append(row[9])
#            arow_2.append(1)
#        
#        A.append(arow_1)
#        A.append(arow_2)
#        B.append(FE[1][2]*10000)
#        B.append(10000)
#        
#        #maximise
#        res = opt.linprog(C, A_ub=A, b_ub=B, options={"disp": True})
#        
#        if config == target[0]:
#            tc = "Both"
#        elif config == target[1]:
#            tc = "GAS"
#        else:
#            tc = "HEV"
#            
#        print '\n\nFor OEM : '+key+'\nTech Choice : '+tc+'\tYear :'+year
#        print (res)
        
#    results = optimize(targetRows_both, FE, Gas);
#    print '\n\nFor OEM : '+key+'\nTech Choice : both\tYear :'+year
#    
#    for row in results:
#        print'\nBrand : '+str(row[1])+'\tSegment : '+str(row[2])
#        print 'Vehicle : '+str(row[3])+'\tVariableCost($) : '+str(row[7])
#        print 'Footprint(feet^2) : '+str(row[8])+'\tFuel Ecobomy(MPG) : '+str(row[9])
#        print '\nAverage Number of vehicles that should be produced : '+str(int(row[10]))
#        print '---------------------------------------------------------------------'
