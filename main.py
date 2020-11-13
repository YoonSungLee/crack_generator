import os
import shutil
import argparse
import random
import numpy as np
import cv2
import imgaug as ia
import imgaug.augmenters as iaa
from imgaug.augmentables.segmaps import SegmentationMapsOnImage
from augmentation import seq, sometimes

def crack_seg(img, pos):
    return (img*pos).astype(np.uint8)

# str2bool reference
# https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--image_path', default='image', help='crack image path')
    parser.add_argument('--mask_path', default='mask', help='crack mask path')
    parser.add_argument('--background_path', default='background', help='background image path')
    parser.add_argument('--augmentation', default=False, type=str2bool, help='whether to use augmentation or not')
    args = parser.parse_args()
    image_path = args.image_path
    mask_path = args.mask_path
    back_path = args.background_path

    images = os.listdir(image_path)
    masks = os.listdir(mask_path)
    backs = os.listdir(back_path)

    if not os.path.isdir('output'):
        os.makedirs('output/images')
        os.makedirs('output/masks')
    if not os.path.isdir('output/images'):
        os.makedirs('output/images')
    if not os.path.isdir('output/masks'):
        os.makedirs('output/masks')


    for idx, back in enumerate(backs):
        # background image load
        img = cv2.imread(os.path.join(back_path, back), cv2.IMREAD_COLOR)
        img = cv2.resize(img, (448, 448), interpolation=cv2.INTER_AREA) # resize (448, 448)

        # crack image and mask random choice
        choice_ = random.choice(images)
        crack_img = cv2.imread(os.path.join(image_path, choice_), cv2.IMREAD_COLOR)
        crack_mask = cv2.imread(os.path.join(mask_path, choice_), cv2.IMREAD_GRAYSCALE)


        # augmentation
        # Reference(https://imgaug.readthedocs.io/en/latest/source/examples_basics.html)
        if args.augmentation:
            segmask = SegmentationMapsOnImage(crack_mask, shape=crack_img.shape)
            crack_img, crack_mask = seq(image=crack_img, segmentation_maps=segmask)
            crack_mask = crack_mask.arr[:,:,0]  # convert to array

        crack_mask_origin = crack_mask.copy()
        crack_mask_origin = np.where(crack_mask_origin >= 128, 255, 0).astype(np.uint8)
        crack_mask = np.where(crack_mask >= 128, 1, 0).astype(np.uint8)
        crack_mask = np.stack((crack_mask, crack_mask, crack_mask), axis=2)



        # only crack and position segmentation
        crack = crack_seg(crack_img, crack_mask)

        # overlap crack on background
        img = ((img*(1-crack_mask)) + crack).astype(np.uint8)
        file_name = 'cvt_'+str(idx+1).zfill(4)+'_'+choice_
        cv2.imwrite(os.path.join('output/images', file_name), img)
        cv2.imwrite(os.path.join('output/masks', file_name), crack_mask_origin)

    print('finished')
