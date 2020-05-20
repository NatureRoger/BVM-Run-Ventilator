# This file is part of the BVM-run Ventilator suite, it's based on 
# Printrun.
#
# BVM-run and Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.


import sqlite3

global db
db = sqlite3.connect('OSCMSTAIWAN.db')

global debug_mod
debug_mod =0

## Get Stoke (X value) from Calibrated  Strok_Volumn mapping table
def DB_Volumn_Get_Stoke(db, BVM_id, V_mL, debug_mod=0):

    Lower_id= 0
    Lower_VmL= 0
    Lower_Stoke= 0

    upper_id= 0
    upper_Stoke= 0          
    upper_VmL= 0

    cursor = db.cursor()
    ## Search Stoke by the Volumn value
    if(V_mL> 900) :
        print ('<<<Error>>> V_mL Must under 900mL , force it to 900mL!')
        V_mL = 900

    Query_str1 = """Select id, Stoke, Volumn from Strok_Volumn where (id=%s and Volumn=%s) order by Volumn""" % (BVM_id, V_mL)         
    if (debug_mod>0) : print (Query_str1)
    cursor.execute(Query_str1) 

    for row in cursor:
        if (debug_mod>0) : print ("BVM_id = %s" % row[0])
        if (debug_mod>0) : print ("Stoke  = %s" % row[1])
        if (debug_mod>0) : print ("Volumn = %s" % row[2])
        return row[1]


    ### Get Upper Strok 
    Query_str1 = """Select id, Stoke, Volumn from Strok_Volumn where (id=%s and Volumn>%s) order by Volumn LIMIT 1""" % (BVM_id, V_mL)
    if (debug_mod>0) : print (Query_str1)
    cursor.execute(Query_str1)

    for row in cursor:
        if (debug_mod>0) : print ('Got upper')
        upper_id= row[0]
        upper_Stoke= row[1]         
        upper_VmL= row[2]

    ### Get Lower Strok
    Query_str1 = """Select id, Stoke, Volumn from Strok_Volumn where (id=%s and Volumn<%s) order by Volumn DESC LIMIT 1""" % (BVM_id, V_mL)
    if (debug_mod>0) : print (Query_str1)
    cursor.execute(Query_str1)

    for row in cursor:
        if (debug_mod>0) : print ('Got Lower')
        Lower_id= row[0]            
        Lower_Stoke= row[1]         
        Lower_VmL= row[2]

    if (upper_VmL ==0 and Lower_VmL ==0):
        Stoke =0
    else:
        Stoke =  (V_mL - Lower_VmL ) / (upper_VmL - Lower_VmL) * (upper_Stoke - Lower_Stoke ) +  Lower_Stoke

    return int(Stoke)    


## Calculate the proper F value of a G-Code (G0 X100 F??) for a Move command line
def DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod=0):

    if (x1==x2):
        print ('<<<Error>>> x=0 move F Value is 0.')
        Fvalue=0
        return Fvalue

    Stoke= abs(x1-x2) 

    vSecond1000 = int( total_x / Stoke * t * 1000) 
    if (debug_mod>0) : print ("===> Delta X = %s , t= %s, vSecond1000 = %s " % (Stoke,t, vSecond1000) )

    cursor = db.cursor()

    upper_Fvalue= 0          
    upper_second1000= 0

    Lower_Fvalue= 0
    Lower_second1000= 0

    Query_str1 = """Select speed, second1000 from GCodeF_Time where (second1000=%s) order by second1000""" % (vSecond1000) 
    if (debug_mod>0) : print ('    '+Query_str1)
    cursor.execute(Query_str1)
    for row in cursor:
        Fvalue= row[0]
        GETsecond1000= row[1] 
        if (debug_mod>0) : print ('    Fvalue=%s ; second1000=%s' % (Fvalue, GETsecond1000) )
        return Fvalue


    ### Get Upper F Value
    Query_str1 = """Select speed, second1000 from GCodeF_Time where (second1000<%s) order by second1000 DESC LIMIT 1 """ % (vSecond1000) 
    if (debug_mod>0) : print ('    '+Query_str1)
    cursor.execute(Query_str1)
    for row in cursor:
        if (debug_mod>0) : print ('    Got upper')
        upper_Fvalue= row[0]
        upper_second1000= row[1]
        if (debug_mod>0) : print ('    upper_Fvalue=%s ; upper_second1000=%s' % (upper_Fvalue, upper_second1000) )  

    ###  vSecond1000 is smaller then second1000 , the speed request is more faster , its beyound the motor limitation.
    if (upper_Fvalue==0):
        Fvalue=50000
        if (debug_mod>0) : print ('    Fvalue=%s' % Fvalue)
        return Fvalue


    ### Get Lower F Value  
    Query_str1 = """Select speed, second1000 from GCodeF_Time where (second1000>%s) order by second1000 LIMIT 1 """ % (vSecond1000) 
    if (debug_mod>0) : print ('    '+Query_str1)
    cursor.execute(Query_str1)
    for row in cursor:
        if (debug_mod>0) : print ('    Got Lower')
        Lower_Fvalue= row[0]
        Lower_second1000= row[1] 
        if (debug_mod>0) : print ('    Lower_Fvalue=%s ; Lower_second1000=%s' % (Lower_Fvalue, Lower_second1000) )

    ###  vSecond1000 is lower then lowest DB second1000 , the speed request is more lower ,
    ###  use the lowest F Value.
    if (upper_Fvalue==0):
        Fvalue=2000
        if (debug_mod>0) : print ('    Fvalue=%s' % Fvalue)
        return Fvalue

    Fvalue = int ((vSecond1000 - upper_second1000 ) / (Lower_second1000 - upper_second1000) * (upper_Fvalue - Lower_Fvalue ) +  Lower_Fvalue)

    if (debug_mod>0) : print ('    Fvalue=%s' % Fvalue)
    coefficient_adj = 1+ (50000+Fvalue)/500000 
    Fvalue = int (Fvalue * coefficient_adj)

    if Fvalue > 50000 :
        Fvalue = 50000 + 9

    if (debug_mod>0) : print ('    after adj Fvalue=%s, coefficient_adj=%s' % (Fvalue, coefficient_adj) )

    #if Fvalue < 4000 :
    #   Fvalue = Fvalue + 300 

    return Fvalue


###-End-##################### Add by Roger  2020-04-26  


#str(DB_Volumn_Get_Stoke(db, 2, 801, 0))
debug_mod=0   # CHANGE TO 1  for more details variables print out for debugging

print ('Get the Stoke X via the Air Volumn mL squided out')
Volumn=910
x = DB_Volumn_Get_Stoke(db, 2,Volumn)
print ('Volumn = %s ; x = %s ' % (Volumn , x ))

Volumn =885
x = DB_Volumn_Get_Stoke(db, 2,Volumn)
print ('Volumn = %s ; x = %s ' % (Volumn , x ))

Volumn =785
x = DB_Volumn_Get_Stoke(db, 2,Volumn)
print ('Volumn = %s ; x = %s ' % (Volumn , x ))

Volumn =685
x = DB_Volumn_Get_Stoke(db, 2,Volumn)
print ('Volumn = %s ; x = %s ' % (Volumn , x ))

Volumn =585
x = DB_Volumn_Get_Stoke(db, 2,Volumn)
print ('Volumn = %s ; x = %s ' % (Volumn , x ))

Volumn =485
x = DB_Volumn_Get_Stoke(db, 2,Volumn)
print ('Volumn = %s ; x = %s ' % (Volumn , x ))

Volumn =385
x = DB_Volumn_Get_Stoke(db, 2,Volumn)
print ('Volumn = %s ; x = %s ' % (Volumn , x ))

Volumn =285
x = DB_Volumn_Get_Stoke(db, 2,Volumn)
print ('Volumn = %s ; x = %s ' % (Volumn , x ))

Volumn =185
x = DB_Volumn_Get_Stoke(db, 2,Volumn)
print ('Volumn = %s ; x = %s ' % (Volumn , x ))

###

debug_mod=1  # CHANGE TO 1  for more details variables print out for debugging

print ('\n\nGet G-Code G0 Move speed F value VIA Delta(X) and within t <sec>')

total_x = 221  ## 擠壓900mL 的 X STOKE Value 

x1= 0
x2= 221
t = 0.9
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

x1= 0
x2= 221
t = 0.8
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

x1= 0
x2= 221
t = 0.7
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))


x1= 0
x2= 221
t = 0.4
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

x1= 8
x2= 200
t = 0.4
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

x1= 8
x2= 190
t = 0.4
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

x1= 8
x2= 180
t = 0.4
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))


x1= 8
x2= 150
t = 0.4
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

#..

x1= 8
x2= 190
t = 0.5
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

x1= 8
x2= 180
t = 0.5
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

x1= 8
x2= 150
t = 0.5
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

#..

x1= 8
x2= 150
t = 0.8
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

x1= 8
x2= 130
t = 0.8
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

x1= 8
x2= 110
t = 0.8
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

#..

x1= 0
x2= 150
t = 0.6
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

x1= 0
x2= 100
t = 0.6
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

x1= 0
x2= 80
t = 0.6
vSecond1000 = int( total_x / (abs(x2-x1)) * t * 1000)
f=DB_Get_speed_Fvalue(db, x1, x2, total_x, t, debug_mod)
print ('x1 = %s ; x2 = %s ; Delta x = %s; t = %ss => F=%s (vSecond1000=%s) ' % (x1 , x2, abs(x2-x1), t, f, vSecond1000 ))

#db.commit()
db.close()

exit(0)






