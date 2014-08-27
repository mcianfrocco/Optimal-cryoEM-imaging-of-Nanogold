#!/usr/bin/env python 

import optparse
from sys import *
import os,sys,re
from optparse import OptionParser
import glob
import subprocess
from os import system
import linecache
import time

#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.set_usage("%prog --micros=<micrographs> --box=<boxfiles> -o <output stack name.img> ")
        parser.add_option("--micros",dest="micros",type="string",metavar="FILE",
                help="Path to micrographs (.mrc)")
        parser.add_option("--box",dest="box",type="string",metavar="FILE",
                help="Path to box files")
	parser.add_option("-o",dest="stack",type="string",metavar="FILE",
                help="Output stack name (.img)")
	parser.add_option("--bin",dest="boxBin",type="int", metavar="INT",default=1,
                help="Optional: Binning factor used during boxer picking")
	parser.add_option("--invert", action="store_true",dest="invert",default=False,
                help="Invert contrast of micrographs")
	parser.add_option("--boxsize",dest="boxsize",type="int", metavar="INT",default=1,
                help="Optional: box size for final stack. (Default is size used in boxer picking)")
	parser.add_option("--phaseflip", action="store_true",dest="phaseFlip",default=False,
                help="Flag to phase flip particles")
        parser.add_option("--ctf",dest="ctf",type="string", metavar="STRING",
                help="CTFFIND output file (ctf_param.txt)")
	parser.add_option("--noinsideonly", action="store_true",dest="noinsideonly",default=False,
                help="Flag to NOT exclude particles on edges of images (needed for tilt pairs)")
	parser.add_option("--perPartCTF", action="store_true",dest="perPartCTF",default=False,
                help="Flag to output a list of per-particle CTF information")
	parser.add_option("-d", action="store_true",dest="debug",default=False,
                help="debug")
        options,args = parser.parse_args()

        if len(args) > 0:
                parser.error("Unknown commandline options: " +str(args))

        if len(sys.argv) < 3:
                parser.print_help()
                sys.exit()
        params={}
        for i in parser.option_list:
                if isinstance(i.dest,str):
                        params[i.dest] = getattr(options,i.dest)
        return params

#=============================
def checkConflicts(params):
        if params['phaseFlip']:
		if not os.path.exists(params['ctf']):
                	print "\nError: ctf file '%s' does not exist\n" % params['ctf']
                	sys.exit()

        if os.path.exists(params['stack']):
                print "\nError: output stack already exists, exiting.\n"
                sys.exit()

	if params['perPartCTF'] is True:

		if os.path.exists('%s_perPartCTF.txt' %(params['stack'][:-4])):

			print "\nError: per particle CTF file already exists, %s_perPartCTF.txt\n" %(params['stack'][:-4])
			sys.exit()

#==============================
def makeStack(params):

	microList = sorted(glob.glob('%s/*.box' %(params['box'])))

	if len(microList) == 0:
		print "\nError: No box files in %s\n" (params['box'])
		sys.exit()	

	for micro in microList:
		microName = micro.split('/')

		#Find corresponding box file
		if os.path.exists('%s/%s.mrc' %(params['box'],microName[-1][:-4])):
			
			if params['phaseFlip'] is True:
				print "\nPhase flipping %s.mrc\n" %(microName[-1][:-4])
                        	microNew = phaseFlipMRC(params,'%s.mrc'%(microName[-1][:-4]))
                	if params['phaseFlip'] is False:
                        	microNew = '%s.mrc'%(microName[-1][:-4])

			print '\nBoxing %s using %s\n' %(microNew,microName[-1]) 
			box = microName[-1]

			if params['invert'] is True:
				cmd = 'proc2d %s %s_inv.mrc invert' %(microNew,microNew[:-4])
				subprocess.Popen(cmd,shell=True).wait()
				micro = '%s_inv.mrc' %(microNew[:-4])
			
			if params['boxsize'] == 1:
				if params['noinsideonly'] is False:
					cmd = 'batchboxer input=%s dbbox=%s output=%s scale=%s insideonly'%(microNew,box,params['stack'],str(params['boxBin']))
					subprocess.Popen(cmd,shell=True).wait()

				if params['noinsideonly'] is True:
                                        cmd = 'batchboxer input=%s dbbox=%s output=%s scale=%s'%(microNew,box,params['stack'],str(params['boxBin']))
                                        subprocess.Popen(cmd,shell=True).wait()

			if params['boxsize'] > 1:
                                if params['noinsideonly'] is False:
					cmd = 'batchboxer input=%s dbbox=%s output=%s scale=%s insideonly newsize=%s insideonly'%(microNew,box,params['stack'],str(params['boxBin']),str(params['boxsize']))
					subprocess.Popen(cmd,shell=True).wait()
	
				if params['noinsideonly'] is True:
					cmd = 'batchboxer input=%s dbbox=%s output=%s scale=%s insideonly newsize=%s '%(microNew,box,params['stack'],str(params['boxBin']),str(params['boxsize']))
                                        subprocess.Popen(cmd,shell=True).wait()


			if params['perPartCTF'] is True:

				perPartCTF(params,'%s%s.mrc'%(params['micros'],microName[-1][:-4]),box,'%s_perPartCTF.txt' %(params['stack'][:-4]))

#============================
def perPartCTF(params,micro,box,outfile):

	#Get number of lines in .box file

	numParts = len(open(box,'r').readlines())

	if params['debug'] is True:
		print micro

	df1,df2,astig = getCTFparam(params['ctf'],micro) 

	i = 1

	while i <= numParts: 

		if i == 1:

			ctf = '%s\t%s\t%s\n' %(df1,df2,astig)
			i = i + 1
			continue

		ctf+= '%s\t%s\t%s\n' %(df1,df2,astig)

		i = i + 1

	if os.path.exists(outfile):
	
		with open(outfile,'a') as myfile: 
			myfile.write(ctf)

	if not os.path.exists(outfile):

		with open(outfile,'w') as myfile:
			myfile.write(ctf)

#=============================
def phaseFlipMRC(params,micro):

	#Convert to spider
	if os.path.exists('%s.spi' %(micro[:-4])):
		os.remove('%s.spi' %(micro[:-4]))
	cmd = 'proc2d %s %s.spi' %(micro,micro[:-4])
	subprocess.Popen(cmd,shell=True).wait()

	#Read in parameters: 6.2,120,2.15,0.15 #cs,ht,apix,ampcontrast

	paramline = linecache.getline(params['ctf'],1)
	lineparam = paramline.split(',')
	cs = lineparam[0]
	kev = lineparam[1]
	apix = lineparam[2]
	contrast = lineparam[3]

	#Get defocus
	df1,df2,astig = getCTFparam(params['ctf'],micro)	

	df = (float(df1)+float(df2))/2

	#Write spider phase flip script	
	ctfFile = createCTFfile(4096,df,apix,kev,cs,contrast)

	#Phase flip micrograph
	flippedMicro = phaseFlipMicro('%s.spi'%(micro[:-4]),ctfFile)

	#Convert back to mrc
	cmd = 'proc2d %s %s.mrc' %(flippedMicro,flippedMicro[:-4])
	subprocess.Popen(cmd,shell=True).wait()

	return '%s.mrc' %(flippedMicro[:-4])
#===========================
def phaseFlipMicro(micro,ctfFile):

	spi='FT\n'
	spi+='%s@1\n' %(micro[:-4])
	spi+='_1\n' 
	spi+='MU\n'
	spi+='_1\n'
	spi+='%s\n' %(ctfFile[:-4])
	spi+='_2\n'
	spi+='*\n'
	spi+='FT\n'
	spi+='_2\n'
	spi+='%s_flipped\n'%(micro[:-4])
	runSpider(spi)

	flipped = os.path.abspath('%s_flipped.spi' %(micro[:-4]))
	
	return flipped

#============================
def getCTFparam(ctf,micro):
	
	ctflines = open(ctf,'r')

	for ctfline in ctflines:
		l = ctfline.split()
		if l[0] == micro:
			df1 = l[1]
			df2 = l[2]
			astig = l[3]
	ctflines.close()	

	return df1,df2,astig
	
#=============================
def createCTFfile(box,df,apix,kev,cs,contrast):

	if os.path.exists('ctf_tmp.spi'):
		os.remove('ctf_tmp.spi')

	spi=';____________ENTER__PARAMETERS__________________\n'
	spi+='X50=%f\n'%(float(cs))
	spi+='X51=%f\n'%((float(kev)*0.0336)/120) 
	spi+='X52=%f\n'%(box)
	spi+='X53=%f\n' %(1/(2*float(apix)))
	spi+='X54=0.0047\n'
        spi+='X55=100\n'
	spi+='X58=%f\n' %(float(contrast))
	spi+='X59=0.15\n' 
	spi+='X60=-1 ;-1 to keep the same contrast as input stack\n'
	spi+=';_______________________________________________\n'
	spi+='MD\n'
	spi+='SET MP\n'
	spi+='4\n'
        spi+='TF CT\n'
	spi+='ctf_tmp\n'
	spi+='X50             ; CS[mm]\n'
        spi+='X23,X51         ; defocus, lambda\n'
        spi+='X52             ; dimensions of output array (box size)\n'
        spi+='X53             ; max spatial freq\n'
        spi+='X54,X55         ; source size, defocus spread\n'
        spi+='0,0	      ; astigmatism correction\n'
        spi+='X58,x59         ; amp contrast\n'
        spi+='X60             ; sign\n'
	runSpider(spi)
	return 'ctf_tmp.spi'

#=============================
def runSpider(lines):
       spifile = "currentSpiderScript.spi"
       if os.path.isfile(spifile):
               os.remove(spifile)
       spi=open(spifile,'w')
       spi.write("MD\n")
       spi.write("TR OFF\n")
       spi.write("MD\n")
       spi.write("VB OFF\n")
       spi.write("MD\n")
       spi.write("SET MP\n")
       spi.write("(4)\n")
       spi.write("\n")
       spi.write(lines)

       spi.write("\nEN D\n")
       spi.close()
       spicmd = "spider spi @currentSpiderScript"
       spiout = subprocess.Popen(spicmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stderr.read()
       output = spiout.strip().split()
       if "ERROR" in output:
               print "Spider Error, check 'currentSpiderScript.spi'\n"
               sys.exit()
       # clean up
       os.remove(spifile)
       if os.path.isfile("LOG.spi"):
               os.remove("LOG.spi")
       resultf = glob.glob("results.spi.*")
       if resultf:
               for f in resultf:
                       os.remove(f)

#==============================
if __name__ == "__main__":

        params=setupParserOptions()
        checkConflicts(params)
	makeStack(params)

	#Clean up
	if params['phaseFlip'] is True:
		flip = glob.glob('*flipped.*')

		for fli in flip:
			os.remove(fli)
