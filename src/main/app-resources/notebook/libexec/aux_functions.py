#!/opt/anaconda/bin/python

import sys
import os
import string
import numpy as np
import gdal
from osgeo import ogr, osr
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
        
    if input_image.startswith('ftp://') or input_image.startswith('http'):
        try:
            dataset = gdal.Open('/vsigzip//vsicurl/%s' % input_image)
        except Exception as e:
            print(e)
    elif '.nc' in input_image:
        dataset = gdal.Open('NETCDF:' + input_image + ':' + product_type)

    polygon_ogr = ogr.CreateGeometryFromWkt(polygon_wkt)
    envelope = polygon_ogr.GetEnvelope()
    bounds = [envelope[0], envelope[3], envelope[1], envelope[2]]         

    gdal.Translate(output_path, dataset, outputType=gdal.GDT_Float32, projWin=bounds, projWinSRS='EPSG:4326')

    dataset = None


def write_output_image(filepath, output_matrix, image_format, data_format, mask=None, output_projection=None, output_geotransform=None, no_data_value=None):
    
    driver = gdal.GetDriverByName(image_format)
    
    out_rows = np.size(output_matrix, 0)
    out_columns = np.size(output_matrix, 1)
    
    output = driver.Create(filepath, out_columns, out_rows, 1, data_format)
    
    if mask is not None and mask is not 0:
            
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
    
    gdal.Warp(filepath, output, format="GTiff", outputBoundsSRS='EPSG:4326')
    
    
def calc_max_matrix(mat1, mat2, no_data_value=None):
    if no_data_value is not None:
        if not isinstance(mat1, int):
            mat1[(mat1 == no_data_value)] = 0
        if not isinstance(mat2, int):
            mat2[(mat2 == no_data_value)] = 0
    
    return np.where(mat1 > mat2, mat1, mat2)

#
# sums mat1 to mat2
# adds 1 to mat_n_vals where != no_data_value 
#
def matrix_sum_for_avg(mat1, mat2, mat_n_vals, no_data_value):

    no_data_value_alt = -9999
    
    mat2_0and1s = np.zeros(mat2.shape)
    
    mat2_0and1s[mat2 != no_data_value] = 1
    
    
    mat_n_vals = mat2_0and1s;
    
    
    #msum = mat1
    
    msum = np.copy(mat1)
    
    msum[mat2 != no_data_value] = mat1[mat2 != no_data_value] + mat2[mat2 != no_data_value]
    
    msum = np.where(np.logical_and(mat1 == no_data_value_alt, mat2 != no_data_value), mat2, msum)
    
    msum[np.logical_and(mat1 == no_data_value_alt, mat2 == no_data_value) ] = no_data_value

    
    
    #msum = mat1 + mat2

    return msum, mat_n_vals


#
# calcs avg of matrix_list
# it takes into account pixels with no_data_values in the time series 
# faster than calc_average_circular_mean
#
def calc_average(matrix_list, n_matrix, no_data_value=None):

    no_data_value_alt = -9999
    
    if not isinstance(matrix_list, list):
        return 0
    
    result = np.copy(matrix_list[0])
    
    result = np.where(result == no_data_value, no_data_value_alt, result)
  
    mat_n_vals = np.zeros(result.shape)
    mat_n_vals[result != no_data_value_alt] = 1
    
    for i in range(1, len(matrix_list)):
     
        result, mat_n_vals_of_sum = matrix_sum_for_avg(result, matrix_list[i], mat_n_vals, no_data_value)
        
        #result = np.copy(result_temp)
        
        mat_n_vals = mat_n_vals + mat_n_vals_of_sum
    

    # to avoid division by 0!!
    mat_n_vals[mat_n_vals == 0] = no_data_value_alt

    result = np.divide(result, mat_n_vals)
    
    # set as no data value pixels that are no data values in all time series
    result[mat_n_vals == no_data_value_alt] = no_data_value
    
    return result


def get_matrix_list(image_list):
    mat_list = []
    for img in image_list:
        dataset = gdal.Open(img)
        product_array = dataset.GetRasterBand(1).ReadAsArray()
        mat_list.append(product_array)
        dataset = None
    return mat_list