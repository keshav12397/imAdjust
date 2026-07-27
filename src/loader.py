import nd2
import cv2
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from scipy import ndimage
import traceback
import re 


def organizeFiles(animalDir):
    '''
    Inefficient way to organize the individual sections with their prescan. im sure i could do something faster w regex but this will not be the ratelimiting step 
    '''

    holdPath = []
    holdCart = []
    holdSlide = []
    for root,dir, files in animalDir.walk():
        if 'reimage' not in dir: ##skip reimage directory for now 
            for file in files:
                if "Region" not in file: # these are all the prescan files 
                    assert 'Channel395' in file #just make sure this was using DAPI
                    holdPath.append(root/file)
                    kms = file.split("_")[0]
                    thisCart = kms.split("-")[0].replace('Slide',"")
                    thisSlide = kms.split("-")[1]

                    holdCart.append(int(thisCart))
                    holdSlide.append(int(thisSlide))

    useOrd = np.lexsort([holdCart,holdSlide]) #order by cassette, then slide 

    useDict = {}
    for mm in useOrd:
        thisPre = holdPath[mm] 
        searchStr = thisPre.name.split("_")[0]

        holdregion = []
        for root,dir,files in animalDir.walk():
            for file in files:
                if file.startswith(searchStr) and "Region" in file: ##dont double include prescan here 
                    holdregion.append(root/file)

        useDict[thisPre] = holdregion

    return useDict

def doPrescan(prescanPath):
    with nd2.ND2File(prescanPath) as ndfile:
        vox = ndfile.voxel_size()
        assert vox.x == vox.y 

        voxFct = vox.x
        mask = ndfile.binary_data.asarray()[0,:,:] #remove empty first dim 
        img = ndfile.asarray() ##actual prescan img 


    hold_roi_med = {}
    for r in range(1,mask.max() + 1):
        r_coords = np.c_[np.where(mask ==r)]  
        med = np.median(r_coords,axis = 0)
        hold_roi_med[r] = np.array([med[1],med[0]])
        # hold_roi_med.append((med[1],med[0])) ### convert this to microns ? I would just multiply the index by the voxFct, origin is always the top left ? 

    #get edges from the binary mask 
    mask2 = mask.astype(bool)
    dx = ndimage.sobel(mask2,axis = 0)
    dy = ndimage.sobel(mask2,axis = 1)
    edged = np.hypot(dx,dy)
    
    assert edged.shape == img.shape
     
    return img, mask2, hold_roi_med , voxFct

def plotPrescanALL(preScanOutputList,savePath:Path = Path.cwd()):

    #stack all slides to plot 
    allImg = np.vstack([x[0] for x in preScanOutputList])
    allMask = np.vstack([x[1] for x in preScanOutputList])
    fig_width = 5
    fig_height = fig_width * allImg.shape[0] / allImg.shape[1] ##

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    im_min,im_max = np.quantile(allImg,[0.1,0.99])
    np.clip(allImg,int(im_min),int(im_max), out=allImg)
    ax.imshow(allImg, cmap="Blues", origin="upper")
    ax.contour(allMask > 0, levels=[0.5], colors="r", linewidths=0.8)

    ##make bounds for slides this is so stupid 
    #add section number to ROI medians 
    start = 0
    for n,ss in enumerate(preScanOutputList):
        usearr = ss[0]
        end = usearr.shape[0]
        ax.text(100, start+end//2, f'Slide_{n+1}',  rotation=90,
            fontweight="bold",
            fontsize=19,
            ha="center",
            va="center")

        allROIS = ss[2]
        for k,v in allROIS.items():
            ax.text(x = v[0],y = v[1] + start,s = k, fontsize = 9,
            bbox=dict(
            boxstyle="round,pad=0.1",
            facecolor="white",
            edgecolor="none",
            alpha=0.7,
        ),)
        start += end

    ax.axis('off')
    fig.savefig(savePath/'allPreScans.png',dpi = 300,bbox_inches = 'tight') ##reduce DPI? idk
    plt.close(fig)

def chanMetaToRGB(chanmeta):
    '''
    chatgptted regex, parses the channels list in the metadata to build array of RGB colors to use for each channel 
    '''
    if not isinstance(chanmeta,list):
        raise ValueError('chan meta must be a list from the meta ! ')
    
    holdidx = []
    holdrgbarr = []
    for channel_str in chanmeta:
        channel_str = str(channel_str)
        index_match = re.search(r"\bindex=(\d+)", channel_str)
        color_match = re.search(
            r"Color\(r=(\d+),\s*g=(\d+),\s*b=(\d+)",
            channel_str,
        )

        if index_match is None or color_match is None:
            raise ValueError("Could not parse channel index or color.")

        channel_index = int(index_match.group(1))
        r, g, b = map(int, color_match.groups())
        rgbarr = np.array([r,g,b],dtype = int)

        holdidx.append(int(channel_index))
        holdrgbarr.append(rgbarr)

    useord = np.argsort(holdidx)
    finRGB_arr = np.c_[holdrgbarr][useord,:]
    finRGB_arr[-1,:]  = [255,255,255] ##im setting DAPI to grey scale i think itll look inice 
    
    ##norm 0-1
    finRGB_arr = finRGB_arr/255
    return finRGB_arr.astype(np.uint16)
    
def renameSection(name:str):
    '''
    Get rid of all the extra slop in the Nd2 filenames 
    '''
    p1 = name.split('_')[0]
    cassNum =p1.split("-")[0].replace('Slide',"")
    slideNum = p1.split('-')[1]

    p2 = name.split('_')[1]
    sectNum = int(p2.replace('Region',""))

    newname = f'Cas{cassNum}_Slide{slideNum}_Section{sectNum}.png'

    return newname

def doClaheMulti(imgPath,downFct:int=1,saveDir:Path = Path.cwd()):

    try: 
        with nd2.ND2File(imgPath) as ndfile:
            imgArr= ndfile.asarray()
        #    print(ndfile._channel_names)
            allmeta = ndfile.metadata
            rbgArr = chanMetaToRGB(allmeta.channels)

            if ndfile.size < 0.15e9:
                return 

        clipArr = np.array([
            [0.001, 0.998],
            [0.001, 0.998],
            [0.001, 0.998],
        ])

        assert imgArr.shape[0] == rbgArr.shape[0] == clipArr.shape[0]

        nChans = imgArr.shape[0]

        clahe = cv2.createCLAHE(
            clipLimit=8.0, #higher number is more aggressive 
            tileGridSize=(200, 200), ##this is NUMBER of tiles not size of tiles. i should adapt for diff image sizes ? 
            
        )

        enhanced_channels = []
        for c in range(nChans):
            sub = imgArr[c].astype(np.uint16)

            # Local contrast enhancement
            sub_clahe = clahe.apply(sub)

            low_q, high_q = clipArr[c]
            pmin, pmax = np.quantile(sub_clahe, [low_q, high_q])

            if pmax <= pmin:
                raise ValueError(
                    f"Channel {c}: invalid intensity range "
                    f"pmin={pmin}, pmax={pmax}"
                )

            # Clip and stretch to full uint16 range
            sub_scaled = (
                np.clip(sub_clahe, pmin, pmax).astype(np.float32) - pmin
            ) / (pmax - pmin)

            sub_scaled *= np.iinfo(np.uint16).max
            sub_scaled = sub_scaled.astype(np.uint16)

            enhanced_channels.append(sub_scaled)

        # Shape: (channels, height, width)
        finArr = np.stack(enhanced_channels, axis=0)

        # Convert RGB definitions from 0–255 to 0–1 weights
        rgb_weights = np.asarray(rbgArr, dtype=np.float32) #/ 255.0

        # Use float for accumulation to prevent uint16 overflow
        compRGB = np.zeros(
            (*finArr.shape[1:], 3),
            dtype=np.float32,
        )

        for channel, rgb_color in zip(finArr, rgb_weights):
            compRGB += channel[..., None] * rgb_color

        # Prevent overlapping channels from exceeding uint16
        compRGB = np.clip(
            compRGB,
            0,
            np.iinfo(np.uint16).max,
        ).astype(np.uint16)

        # OpenCV expects BGR when saving
        composite_bgr = cv2.cvtColor(compRGB, cv2.COLOR_RGB2BGR)

        h, w = composite_bgr.shape[:2]
        img_small = cv2.resize(composite_bgr, (w // downFct, h // downFct), interpolation=cv2.INTER_AREA)


        usename = renameSection(imgPath.name)### Fix renaming the thing 


        success = cv2.imwrite(saveDir/usename, composite_bgr)
        return composite_bgr
    except Exception:
        print(f"\nError processing file:\n{imgPath}")
        print(f"Requested save directory:\n{saveDir}")
        traceback.print_exc()
        raise
        

def compareClaheSingChan(imgPath,saveDir: Path = Path.cwd()):
    '''
    Plot single channel normal and CLAHE top and bottom to compare 
    '''
    with nd2.ND2File(imgPath) as ndfile:
        imgArr= ndfile.asarray()
    #    print(ndfile._channel_names)
        allmeta = ndfile.metadata
        rbgArr = chanMetaToRGB(allmeta.channels)

        if ndfile.size < 0.15e9:
            return 

    clipArr = np.array([
        [0.001, 0.998],
        [0.001, 0.998],
        [0.001, 0.998],
    ])

    assert imgArr.shape[0] == rbgArr.shape[0] == clipArr.shape[0]
    nChans = imgArr.shape[0]
    clahe = cv2.createCLAHE(
        clipLimit=8.0, #higher number is more aggressive 
        tileGridSize=(200, 200), ##this is NUMBER of tiles not size of tiles. i should adapt for diff image sizes ? 
    )

    hold_norm = []
    hold_clahe = []

    for c in range(nChans):
        sub = imgArr[c].astype(np.uint16)

        # Local contrast enhancement
        sub_clahe = clahe.apply(sub)

        hold_sc = []
        for x in [sub,sub_clahe]:
            low_q, high_q = clipArr[c]
            pmin, pmax = np.quantile(x, [low_q, high_q])

            if pmax <= pmin:
                raise ValueError(
                    f"Channel {c}: invalid intensity range "
                    f"pmin={pmin}, pmax={pmax}"
                )

            # Clip and stretch to full uint16 range
            sub_scaled = (
                np.clip(x, pmin, pmax).astype(np.float32) - pmin
            ) / (pmax - pmin)

            sub_scaled *= np.iinfo(np.uint16).max
            sub_scaled = sub_scaled.astype(np.uint16)
            hold_sc.append(sub_scaled)

        hold_norm.append(hold_sc[0])
        hold_clahe.append(hold_sc[1])

    #now build RGB pannels for everything 
    holdfin_pans = []
    for collist in [hold_norm,hold_clahe]:
        rgb_panels = []
        for chan_img, rgb_color in zip(collist,rbgArr):
            panel = chan_img[...,None].astype(np.float32) * rgb_color[None,None,:]
            panel = np.clip(panel, 0, np.iinfo(np.uint16).max).astype(np.uint16)
            rgb_panels.append(panel)
        holdfin_pans.append(rgb_panels)

    
    
    norm_all = np.hstack(holdfin_pans[0])
    clahe_all = np.hstack(holdfin_pans[1])

    full = np.vstack([norm_all,clahe_all])

    composite_bgr = cv2.cvtColor(full, cv2.COLOR_RGB2BGR)

    h, w = composite_bgr.shape[:2]
    downFct = 4
    img_small = cv2.resize(composite_bgr, (w // downFct, h // downFct), interpolation=cv2.INTER_AREA)

    
    usename = renameSection(imgPath.name)
    usename =  "splitCompare_" + usename.replace('.png','.tiff')
    success = cv2.imwrite(saveDir/usename, img_small,[cv2.IMWRITE_TIFF_COMPRESSION, 1])
    
    return success,img_small








      