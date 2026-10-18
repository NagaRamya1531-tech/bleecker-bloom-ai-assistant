import { useEffect, useState } from 'react';
import { Product, ProductCategory } from '@/types/types';
import { fetchProducts } from '@/services/productService';
import { Text, View, FlatList,StatusBar, useWindowDimensions   } from 'react-native'
import ProductImage from '@/components/ProductImage'
import React from 'react'
import { SafeAreaView } from 'react-native-safe-area-context'
import { GestureHandlerRootView, TouchableOpacity } from "react-native-gesture-handler";
import {router} from "expo-router";
import AntDesign from '@expo/vector-icons/AntDesign';
import Toast from 'react-native-root-toast';
import { useCart } from '@/components/CartContext';
import Banner from '@/components/Banner';
import SearchArea from '@/components/SearchArea';
import { LinearGradient } from 'expo-linear-gradient';

const Home = () => {
  const { width } = useWindowDimensions();
  const numColumns = width >= 1180 ? 4 : width >= 760 ? 3 : 2;

  const { addToCart } = useCart();

  const [products, setProducts] = useState<Product[]>([]);
  const [shownProducts, setShownProducts] = useState<Product[]>([]);
  const [productCategories, setProductCatgories] = useState<ProductCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState('');

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  

  useEffect(() => {
    const uniqueCategories = Array.from((productCategories)).map((category) => ({
      id: category.id,
      selected: selectedCategory === category.id,
    }));
    setProductCatgories(uniqueCategories);

    const normalizedQuery = searchQuery.trim().toLowerCase();
    const filteredProducts = products.filter((product) => {
      const matchesCategory = selectedCategory === 'All' || product.category === selectedCategory;
      const matchesSearch = !normalizedQuery ||
        `${product.name} ${product.category} ${product.description}`.toLowerCase().includes(normalizedQuery);
      return matchesCategory && matchesSearch;
    });
    setShownProducts(filteredProducts);

  }, [selectedCategory, products, searchQuery]);

  useEffect(() => {
    const loadProducts = async () => {
      try {
        const productsData = await fetchProducts();
        

        const categories = productsData.map((product) => product.category);
        categories.unshift('All');
        const uniqueCategories = Array.from(new Set(categories)).map((category) => ({
          id: category,
          selected: selectedCategory === category,
        }));

        setProducts(productsData);
        setShownProducts(productsData);
        setProductCatgories(uniqueCategories);


      } catch (err) {
        setError("Error fetching products"+err);
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadProducts();
  }, []);

  if (loading) return <Text>Loading...</Text>;
  if (error) return <Text>{error}</Text>;

  const addButton = (name:string) => {
    addToCart(name, 1);
    Toast.show(`${name} added to cart`, {
      duration: Toast.durations.SHORT,
    });
  };

  return (
    <GestureHandlerRootView>
      <StatusBar barStyle="light-content" backgroundColor="#203B32" />
      <SafeAreaView className='flex-1'>
        <LinearGradient
          colors={['#CDDDC8', '#F4EEE2', '#E1CCB7']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={{ flex: 1 }}
        >
        <FlatList 
            key={numColumns}
            horizontal={false}
            columnWrapperStyle={{
              justifyContent: 'space-between',
              paddingHorizontal: width >= 1180 ? 32 : 15,
              maxWidth: 1280,
              width: '100%',
              alignSelf: 'center',
            }}
            numColumns={numColumns}
            keyExtractor={(item, index) => index.toString()}
            data= {shownProducts}

            renderItem={({item}) => (
              <View
                style={{ width: `${100 / numColumns - 1}%` }}
                className='mt-3 bg-white rounded-lg p-2 flex justify-between'>
                <TouchableOpacity

                  onPress={() => { 
                    
                    router.push( { pathname: '/details', params: {name: item.name, 
                      image_url: item.image_url,
                      type: item.category, 
                      price: item.price,
                      rating: item.rating,
                      description: item.description,}} ) 
                    }
                  }
                >
                  <ProductImage
                    uri={item.image_url}
                    accessibilityLabel={`${item.name} coffee shop product`}
                    className='w-full rounded-lg'
                    style={{ aspectRatio: 1.28 }}
                    iconSize={36}
                  />
                  <Text
                    className="text-app_ink text-base font-[Sora-SemiBold] ml-1 mt-2"
                  >{item.name}
                  </Text>
                  <Text
                    className="text-[#6E7469] text-xs font-[Sora-Regular] ml-1 mt-1"
                  >{item.category}
                  </Text>
                </TouchableOpacity>

                <View 
                  className="flex-row justify-between ml-1 mt-4 mb-2"
                >
                  <Text
                    className="text-app_ink text-lg font-[Sora-SemiBold] "
                  >
                    ${item.price}
                  </Text>
                  
                    <TouchableOpacity
                      onPress = {() => addButton(item.name)}
                    >
                      <View
                        className='mr-2 p-2 -mt-1 bg-app_orange_color rounded-lg'
                      >
                        <AntDesign name="plus" size={20} color="white" />
                      </View>
                    </TouchableOpacity>

                  </View>
                


              </View>
          )}
          
          ListHeaderComponent={() => (
          <View className='flex'>
            <SearchArea searchQuery={searchQuery} onSearchChange={setSearchQuery} />
            <Banner />
            
            <View className='px-5 pt-6'>
              <Text className='text-app_ink text-xl font-[Sora-SemiBold]'>At the counter</Text>
              <Text className='mt-1 text-[#6E7469] text-sm font-[Sora-Regular]'>A few neighborhood favorites</Text>
              <FlatList 
                className='mt-4 mb-1'
                data = {productCategories}
                horizontal={true}
                renderItem={({item}) => (
                  <TouchableOpacity
                    onPress={() => setSelectedCategory(item.id)}
                  >
                    <Text
                      className={`text-sm mr-2 font-[Sora-Regular] px-4 py-2 rounded-full
                        ${item.selected ? 'text-white' : 'text-[#313131]'}
                        ${item.selected ? 'bg-app_ink ' : 'bg-white '}
                        `}
                      >{item.id}
                    </Text>
                  </TouchableOpacity>
                )}
              />

            </View>

          </View>

          )}
          ListEmptyComponent={() => (
            <View className="mx-5 mt-8 items-center">
              <Text className="text-app_ink text-lg font-[Sora-SemiBold]">Nothing on the counter</Text>
              <Text className="mt-2 text-[#6E7469] text-sm font-[Sora-Regular] text-center">
                Try another search or menu category.
              </Text>
            </View>
          )}
        />
        </LinearGradient>
      </SafeAreaView>
    </GestureHandlerRootView>
  )
}

export default Home