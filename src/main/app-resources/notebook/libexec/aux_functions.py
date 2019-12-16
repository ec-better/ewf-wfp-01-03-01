#!/opt/anaconda/bin/python

import sys
import os
import string
import numpy as np
from osgeo import gdal, ogr, osr
from shapely.wkt import loads

def matrix_sum(mat1, mat2, no_data_value=None):
    if no_data_value is not None:
        if not isinstance(mat1, int):
            mat1[(mat1 == no_data_value)] = 0
        if not isinstance(mat2, int):
            mat2[(mat2 == no_data_value)] = 0
    return mat1 + mat2

def crop_image(input_image, polygon_wkt, output_path, product_type=None):
    dataset = None
    crop_directory = os.path.dirname(output_path)
    if crop_directory is not '' and not os.path.exists(crop_directory):
        os.makedirs(crop_directory)
    if input_image.startswith('ftp://') or input_image.startswith('http'):
        try:
            dataset = gdal.Open('/vsigzip//vsicurl/%s' % input_image)
        except Exception as e:
            print(e)
    elif '.nc' in input_image:
        dataset = gdal.Open('NETCDF:' + input_image + ':' + product_type)
    no_data_value = dataset.GetRasterBand(1).GetNoDataValue()
    geo_t = dataset.GetGeoTransform()
    polygon_ogr = ogr.CreateGeometryFromWkt(polygon_wkt)
    envelope = polygon_ogr.GetEnvelope()
    bounds = [envelope[0], envelope[2], envelope[1], envelope[3]]
    
    gdal.Warp(output_path, dataset, format="GTiff", outputBounds=bounds, srcNodata=no_data_value, dstNodata=no_data_value)
    
def write_output_image(filepath, output_matrix, image_format, data_format, mask=None, output_projection=None, output_geotransform=None, no_data_value=None):
    driver = gdal.GetDriverByName(image_format)
    out_rows = np.size(output_matrix, 0)
    out_columns = np.size(output_matrix, 1)
    if mask is not None and mask is not 0:
        output = driver.Create(filepath, out_columns, out_rows, 2, data_format)
        mask_band = output.GetRasterBand(2)
        mask_band.WriteArray(mask)
        if no_data_value is not None:
            output_matrix[mask > 0] = no_data_value
    else:
        output = driver.Create(filepath, out_columns, out_rows, 1, data_format)
    
    if output_projection is not None:
        output.SetProjection(output_projection)
    if output_geotransform is not None:
        output.SetGeoTransform(output_geotransform)
    
    raster_band = output.GetRasterBand(1)
    if no_data_value is not None:
        raster_band.SetNoDataValue(no_data_value)
    raster_band.WriteArray(output_matrix)
    gdal.Warp(filepath, output, format="GTiff", outputBoundsSRS='EPSG:4326', xRes=output_geotransform[1], yRes=-output_geotransform[5], targetAlignedPixels=True)
    
def calc_max_matrix(mat1, mat2, no_data_value=None):
    if no_data_value is not None:
        if not isinstance(mat1, int):
            mat1[(mat1 == no_data_value)] = 0
        if not isinstance(mat2, int):
            mat2[(mat2 == no_data_value)] = 0
    
    return np.where(mat1 > mat2, mat1, mat2)

def calc_average(matrix_list, n_matrix, no_data_value=None):
    if not matrix_list:
        return 0
    result = matrix_list[0]
    for i in range(1, n_matrix):
        result = matrix_sum(result, matrix_list[i], no_data_value)
    
    return np.divide(result, (n_matrix*1.00))

def get_matrix_list(image_list):
    mat_list = []
    for img in image_list:
        dataset = gdal.Open(img)
        product_array = dataset.GetRasterBand(1).ReadAsArray()
        mat_list.append(product_array)
        dataset = None
    return mat_list