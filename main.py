import os
import shutil
import argparse
import random
import numpy as np
import cv2
import imgaug as ia
import imgaug.augmenters as iaa
from imgaug.augmentables.segmaps import SegmentationMapsOnImage

def crack_seg(img, pos):
    return (img*pos).astype(np.uint8)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--image_path', default='image', help='crack image path')
    parser.add_argument('--mask_path', default='mask', help='crack mask path')
    parser.add_argument('--background_path', default='background', help='background image path')
    parser.add_argument('--augmentation', default=True, type=bool, help='whether to use augmentation or not')
    args = parser.parse_args()
    image_path = args.image_path
    mask_path = args.mask_path
    back_path = args.background_path

    images = os.listdir(image_path)
    masks = os.listdir(mask_path)
    backs = os.listdir(back_path)

    # online augmentation code
    sometimes = lambda aug: iaa.Sometimes(0.5, aug)

    # Define our sequence of augmentation steps that will be applied to every image.
    seq = iaa.Sequential(
        [
            #
            # Apply the following augmenters to most images.
            #
            iaa.Fliplr(0.5),  # horizontally flip 50% of all images
            iaa.Flipud(0.2),  # vertically flip 20% of all images

            # crop some of the images by 0-10% of their height/width
            sometimes(iaa.Crop(percent=(0, 0.1))),

            # Apply affine transformations to some of the images
            # - scale to 80-120% of image height/width (each axis independently)
            # - translate by -20 to +20 relative to height/width (per axis)
            # - rotate by -45 to +45 degrees
            # - shear by -16 to +16 degrees
            # - order: use nearest neighbour or bilinear interpolation (fast)
            # - mode: use any available mode to fill newly created pixels
            #         see API or scikit-image for which modes are available
            # - cval: if the mode is constant, then use a random brightness
            #         for the newly created pixels (e.g. sometimes black,
            #         sometimes white)
            sometimes(iaa.Affine(
                scale={"x": (0.8, 1.2), "y": (0.8, 1.2)},
                translate_percent={"x": (-0.2, 0.2), "y": (-0.2, 0.2)},
                rotate=(-45, 45),
                shear=(-16, 16),
                order=[0, 1],
                # cval=(0, 255),
                mode=ia.ALL
            )),

            #
            # Execute 0 to 5 of the following (less important) augmenters per
            # image. Don't execute all of them, as that would often be way too
            # strong.
            #
            iaa.SomeOf((0, 5),
                       [
                           # Convert some images into their superpixel representation,
                           # sample between 20 and 200 superpixels per image, but do
                           # not replace all superpixels with their average, only
                           # some of them (p_replace).
                           sometimes(
                               iaa.Superpixels(
                                   p_replace=(0, 1.0),
                                   n_segments=(20, 200)
                               )
                           ),

                           # Blur each image with varying strength using
                           # gaussian blur (sigma between 0 and 3.0),
                           # average/uniform blur (kernel size between 2x2 and 7x7)
                           # median blur (kernel size between 3x3 and 11x11).
                           iaa.OneOf([
                               iaa.GaussianBlur((0, 3.0)),
                               iaa.AverageBlur(k=(2, 7)),
                               iaa.MedianBlur(k=(3, 11)),
                           ]),

                           # Sharpen each image, overlay the result with the original
                           # image using an alpha between 0 (no sharpening) and 1
                           # (full sharpening effect).
                           # iaa.Sharpen(alpha=(0, 1.0), lightness=(0.75, 1.5)),

                           # Same as sharpen, but for an embossing effect.
                           # iaa.Emboss(alpha=(0, 1.0), strength=(0, 2.0)),

                           # Search in some images either for all edges or for
                           # directed edges. These edges are then marked in a black
                           # and white image and overlayed with the original image
                           # using an alpha of 0 to 0.7.
                           sometimes(iaa.OneOf([
                               iaa.EdgeDetect(alpha=(0, 0.7)),
                               iaa.DirectedEdgeDetect(
                                   alpha=(0, 0.7), direction=(0.0, 1.0)
                               ),
                           ])),

                           # Add gaussian noise to some images.
                           # In 50% of these cases, the noise is randomly sampled per
                           # channel and pixel.
                           # In the other 50% of all cases it is sampled once per
                           # pixel (i.e. brightness change).
                           iaa.AdditiveGaussianNoise(
                               loc=0, scale=(0.0, 0.05 * 255), per_channel=0.5
                           ),

                           # Either drop randomly 1 to 10% of all pixels (i.e. set
                           # them to black) or drop them on an image with 2-5% percent
                           # of the original size, leading to large dropped
                           # rectangles.
                           iaa.OneOf([
                               iaa.Dropout((0.01, 0.1), per_channel=0.5),
                               iaa.CoarseDropout(
                                   (0.03, 0.15), size_percent=(0.02, 0.05),
                                   per_channel=0.2
                               ),
                           ]),

                           # Invert each image's channel with 5% probability.
                           # This sets each pixel value v to 255-v.
                           # iaa.Invert(0.05, per_channel=True),  # invert color channels

                           # Add a value of -10 to 10 to each pixel.
                           iaa.Add((-10, 10), per_channel=0.5),

                           # Change brightness of images (50-150% of original value).
                           # iaa.Multiply((0.5, 1.5), per_channel=0.5),

                           # Improve or worsen the contrast of images.
                           # iaa.LinearContrast((0.5, 2.0), per_channel=0.5),
                           iaa.LinearContrast((0.5, 1.0), per_channel=0.5),

                           # Convert each image to grayscale and then overlay the
                           # result with the original with random alpha. I.e. remove
                           # colors with varying strengths.
                           iaa.Grayscale(alpha=(0.0, 1.0)),

                           # In some images move pixels locally around (with random
                           # strengths).
                           sometimes(
                               iaa.ElasticTransformation(alpha=(0.5, 3.5), sigma=0.25)
                           ),

                           # In some images distort local areas with varying strength.
                           sometimes(iaa.PiecewiseAffine(scale=(0.01, 0.05)))
                       ],
                       # do all of the above augmentations in random order
                       random_order=True
                       )
        ],
        # do all of the above augmentations in random order
        random_order=True
    )


    for back in backs:
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
        file_name = 'cvt_'+choice_
        cv2.imwrite(os.path.join('output/images', file_name), img)
        cv2.imwrite(os.path.join('output/masks', file_name), crack_mask_origin)

    print('finished')