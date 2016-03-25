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
iterations = 10
deltaPricePercent = 5
deltaQtyPercent = 10
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

#create a 3x3x3x4 size 'prices'/'a' matrix having the prices of all the OEMs for all the years
#where first dimension is the year = 3 options
#second dimension is the OEM = 3 options
#third dimension is the Brand within the OEM  = 3 options
#fourth dimension is each tech choice = 4 options
p = np.array(price)
a = np.zeros((3,3,3,4))
count = 0;
for prices in p:
    #each prices contains 36 options for each year. (12 per OEM)
    a[count] = prices.reshape((3,3,4))
    count = count + 1
 
prices = a
del a,p,price   

#for each year 2016 & 2017
#storing the header row of the strategy data csv
strategy_headings = np.array(Strategy_data)[0]

#converting the strategy data to an np.array format and deleting the header row
strategy = np.delete(np.array(Strategy_data),0,0)

#for each year that the strategies need to be worked out for
for st in strategy:
    year = int(st[0])
    prices_lastyear = np.copy(prices[(year-1)%startYear])
    
    # if any prices of last year are infinity, set them to prices of 'startyear'  
    if float("inf") in prices_lastyear:
        prices_lastyear = prices_lastyear.flatten()
        for i in range (prices_lastyear.size):
            if prices_lastyear[i] == float("inf"):
                prices_lastyear[i] = (prices[0].flatten())[i]
        
        prices_lastyear = prices_lastyear.reshape(3,3,4)
        
              
    #extracting the given stratgey for the 'year' for the respective OEM
    Stgy = {'Ford':st[1].split('&'), 'GM': st[2].split('&'),'Toyota':st[3].split('&')}    
  
    allTargets = []
    #for each OEM  
    for key,value in book.sheets.items():
        prices_updated = np.copy(prices_lastyear)

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
            if (int(row[6]) == int(year)):
                if row[4] in Stgy[key]:
                    prices_updated[oem,(count%12)/4,count%4] = float(row[8])
                else:
                    prices_updated[oem,(count%12)/4,count%4] = float("inf")
                
                
        #running the demand simulation for all the updated prices within my OEM, making no changes to prices of other OEMs                
        q = demand(prices_updated)
        
        #extracting the demand quantities of matches tech choices and adding them to "target" for the optimization        
        count = -1
        for row in value:
            count +=1;
            #for each of the options that satisfy its strategy
            if (int(row[6]) == int(year)):
                if row[4] in Stgy[key]:
                    row.append(q[oem,(count%12)/4,count%4])
                    target.append(row)
        
        
        allTargets.append(target)
        
        #run the optimization algorithm on my 'target' rows
        #using qis as upper bound
        #constraint of sigma qi.ei >= C* sigma qi
        #maximise qi*(pi-ci)
        
        #TO BE REPEATED NUMBER OF ITERATIONS - 1 time UNLESS everything works
        checker = False
        for iter in range (iterations-1):
            if (checker):
                break
            else:
                checker = True
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
                res = opt.linprog(C, A_ub=A, b_ub=B, bounds = bnds, options={"disp": False})
        
                #Check the quantities 'x' that have been produced against each of the quantities in 'target'
                count = -1
                countMatched = 0
                for row in value:
                    count +=1;
                    #for each of the options that satisfy its strategy
                    if (int(row[6]) == int(year)):
                        if row[4] in Stgy[key]:                            
                            if ((target[countMatched][11] - res['x'][countMatched])*(100/target[countMatched][11]) > deltaQtyPercent):
                                checker = False #to ensure the iterations are run again
                                countMatched +=1
                                prices_updated[oem,(count%12)/4,count%4] *= (1+float(deltaPricePercent)/float(100))
                       
                newTarget = []       
                if checker == False:
                    print'%%%something'
                    #call the demand model 
                    q = demand(prices_updated)
                    
                    count = -1
                    countMatched = -1
                    for row in value:
                        count +=1;
                        #for each of the options that satisfy its strategy
                        if (int(row[6]) == int(year)):
                            if row[4] in Stgy[key]:
                                countMatched +=1
                                if ((target[countMatched][11] - res['x'][countMatched])*(100/target[countMatched][11]) > deltaQtyPercent):  
                                    updatedTarget = target[countMatched]
                                    updatedTarget[8] = prices_updated[oem,(count%12)/4,count%4]  
                                    updatedTarget[11] = q[oem,(count%12)/4,count%4]
                                    allTargets[oem][countMatched] = updatedTarget
                                    newTarget.append(updatedTarget)
                    
                    #update a new set of targets on which the optimizer will run
                    target = newTarget
    
        #HAVE TO UPDATE OEM's final price into prices for this year
        prices[(year)%startYear,oem] = np.copy(prices_updated[oem])
        
    
    print '\n\n\n^%^%^%^%^%^%^%^%^%^%^%^%^%^%^%^%^%'
    print '\tFor the year : ' + str(year)
    print '^%^%^%^%^%^%^%^%^%^%^%^%^%^%^%^%^%'
    #NEED TO CHECK DEMAND against Sales
    #Everyone has finished executing for a year
    #Run the demand model on the new year's prices revealed to everyone
    q = demand(prices[year%startYear])  
           
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
                #for the strategies that matched check the new Prices
                row.append(q[oem,(count%12)/4,count%4])
                row[8] = prices[year%startYear,oem,(count%12)/4,count%4]
                target.append(row)
                
        #compare with the each of allTargets[oem]'s values
        print '\n\n#####################'
        print str(key)+' '+str(year)+' - Profits'
        print '#####################'
        countTarget = 0
        for rows in allTargets[oem]:
            print '-----------------------'
            print 'Vehicle: '+str(rows[3])+'; TechChoice: '+str(rows[4])
            #print str(rows[11])+' vs. '+str(target[countTarget][11])
            print 'Profit: ' + str((rows[8]-rows[7])*target[countTarget][11]) #+' OR '+ str((target[countTarget][8]-target[countTarget][7])*target[countTarget][11])
            countTarget+=1