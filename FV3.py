import pyexcel
from pyexcel.ext import xlsx
from pyexcel.ext import xls
import os
import scipy.optimize as opt 

#Take in global background content from csv files - fe & gas
with open(os.path.join('fe.csv'), 'r') as f:
        FE_data = f.readlines()
with open(os.path.join('gas.csv'), 'r') as f:
        Gas_data = f.readlines()

for i in range(len(FE_data)):
    FE_data[i] = FE_data[i].replace('\n','').split(',')    
for i in range(len(Gas_data)):
    Gas_data[i] = Gas_data[i].replace('\n','').split(',')

#book now contains the entire excel workbook      
book = pyexcel.get_book(file_name="FEC game input.xlsx")
year = '2016'

#ideally returns the FUEL EFFICIENCY & COSTS That we have in the xlsx.
def optimize(targetRows, FE, Gas):
    results = [] #empty array
    fe_year = FE[0][0] #take year value
    for row in targetRows:
        #compare that years are equal and FE constraint adheres
       if((str(int(row[6]))==str(fe_year)) and (str(row[9])<=str(FE[1][2]))):
            output = row
            output.append(row[7]/((float(Gas[0][1]) + float(Gas[0][2]))/2 * 0.01))
            results.append(output)               
    return results
        
for key,value in book.sheets.items():
    value.delete_rows([0])
    #TO BE ADDED
    #check whatever options are present in the 'Tech choice' column of the sheet & Store these options in an array	
    
    #for the both permutation 
    targetRows_both = []
    targetRows_gas = []
    targetRows_hev = []
    FE = []
    Gas = []
    target = []
    
    for row in value:
#        print 'ROW[6]' 
#        print row[6], type(row[6]), int(row[6]), type(int(row[6]))
#        print 'year'
#        print year, type(year), int(year), type(int(year))
        if int(row[6]) == int(year):
            targetRows_both.append(row)
            targetRows_gas.append(row) if row[4].lower() == "gas" else targetRows_hev.append(row)             
#            if row[4].lower() == "gas":
#                targetRows_gas.append(row)
#            else:
#                targetRows_hev.append(row) 
                       
    
    #appending into FE the 'year's' data                       
    for row in FE_data:
        if(str(row[0])==year):
            FE.append(row)
    
    #appending into Gas the 'year's' data      
    for row in Gas_data: 
        if(str(row[0])==year):
            Gas.append(row)
    
    target.append(targetRows_both)
    target.append(targetRows_gas)
    target.append(targetRows_hev)
    
    for config in target:
        length = len(config)
        print length       
        C = []
        A = []
        B = []
        arow_1 = []
        arow_2 = []
        #C has to have all the profit values that are to MAX
        #A's first row has to have the coefficients of CAFE = 1 eqn
        #A's second row has to have coefficients of number of cars = 1
        #B has to have the value for CAFE & number of cars
        for row in config:
            C.append(row[7]*-1)
            arow_1.append(row[9])
            arow_2.append(1)
        
        A.append(arow_1)
        A.append(arow_2)
        B.append(FE[1][2]*10000)
        B.append(10000)
        
        #maximise
        res = opt.linprog(C, A_ub=A, b_ub=B, options={"disp": True})
        
        if config == target[0]:
            tc = "Both"
        elif config == target[1]:
            tc = "GAS"
        else:
            tc = "HEV"
            
        print '\n\nFor OEM : '+key+'\nTech Choice : '+tc+'\tYear :'+year
        print (res)
        
#    results = optimize(targetRows_both, FE, Gas);
#    print '\n\nFor OEM : '+key+'\nTech Choice : both\tYear :'+year
#    
#    for row in results:
#        print'\nBrand : '+str(row[1])+'\tSegment : '+str(row[2])
#        print 'Vehicle : '+str(row[3])+'\tVariableCost($) : '+str(row[7])
#        print 'Footprint(feet^2) : '+str(row[8])+'\tFuel Ecobomy(MPG) : '+str(row[9])
#        print '\nAverage Number of vehicles that should be produced : '+str(int(row[10]))
#        print '---------------------------------------------------------------------'