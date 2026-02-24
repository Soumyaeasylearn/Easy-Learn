// App.js — React Native entry point
import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { StatusBar, Text } from "react-native";

import HomeScreen   from "./screens/HomeScreen";
import LessonScreen from "./screens/LessonScreen";
import ProfileScreen from "./screens/ProfileScreen";

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerStyle: { backgroundColor: "#0a0a0f", borderBottomColor: "#1e1e2e" },
          headerTintColor: "#e8e8f0",
          tabBarStyle: { backgroundColor: "#0a0a0f", borderTopColor: "#1e1e2e" },
          tabBarActiveTintColor: "#7fff6e",
          tabBarInactiveTintColor: "#6b6b82",
          tabBarIcon: ({ focused, color }) => {
            const icons = { Home: "🏠", Practice: "🎙", Profile: "👤" };
            return <Text style={{ fontSize: focused ? 22 : 18 }}>{icons[route.name]}</Text>;
          },
        })}
      >
        <Tab.Screen name="Home"     component={HomeScreen}    options={{ title: "SpeakUp" }} />
        <Tab.Screen name="Practice" component={LessonScreen}  />
        <Tab.Screen name="Profile"  component={ProfileScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
