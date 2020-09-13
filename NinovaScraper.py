# -*- coding: utf-8 -*-
import time
import sys
import os
from os.path import isfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from shutil import move
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from Constants import *
import getpass # Hides the password while the user is typing in the console


class InputBox:
	def __init__(self, input, identifier):
		self.input = input
		self.identifier = identifier

	def __call__(self, driver):
		if (self.identifier is BY_ID):
			element = driver.find_element_by_id(self.input)
		elif (self.identifier is BY_NAME):
			element = driver.find_element_by_name(self.input)
		elif (self.identifier is BY_CLASS):
			element = driver.find_element_by_class_name(self.input)
		elif (self.identifier is BY_TAG):
			element = driver.find_element_by_tag_name(self.input)
		if element:
			return element
		else:
			return False


class Ninova:

	def __init__(self, username, password):
		self.url = NINOVA_URL
		self.downloads_folder = os.path.join(os.getcwd(), "downloads")
		if(not os.path.exists(self.downloads_folder)):
			os.mkdir(self.downloads_folder)
		options = Options()
		options.headless = False
		options.add_experimental_option("prefs", {
			"download.default_directory": self.downloads_folder,
			"download.prompt_for_download": 'false',
			"download.directory_upgrade": 'true',
			"safebrowsing.enabled": 'false',
			"download_restrictions": 0
		})
		if("win" in sys.platform):
			dr = "./driver/chromedriver"
		elif ("linux" in sys.platform):
			dr = "./driver/chromedriver_linux"
		else:
			dr = "./driver/chromedriver_mac"

		self.driver = webdriver.Chrome(dr, options=options)
		self.downloadList = []
		self.username = username
		self.password = password


	def waitFor(self, input, identifier):
		return WebDriverWait(self.driver, 10).until(InputBox(input, identifier))

	def login(self):
		self.driver.get(self.url)
		oturumAc = self.waitFor(OTURUM_AC, BY_ID)
		if (not oturumAc is False):
			oturumAc.click()
		kullaniciAdi = self.waitFor(KULLANICI_ADI, BY_NAME)
		sifre = self.waitFor(SIFRE, BY_NAME)
		giris = self.waitFor(GIRIS, BY_NAME)

		kullaniciAdi.send_keys(self.username)
		sifre.send_keys(self.password)
		giris.click()
		time.sleep(2)

	def start(self):
		courseLinks = self.getCourses()
		for i in range(0, len(courseLinks)):
			courseLinks[i].click()
			cur_url = self.driver.current_url
			courseName = self.getCourseName(cur_url)

			current_course_folder = os.path.join(
				self.downloads_folder, courseName)
			if(not os.path.exists(current_course_folder)):
				os.mkdir(current_course_folder)  # Open a folder for the course

			links = [cur_url+"/SinifDosyalari", cur_url+"/DersDosyalari"]
			for link in links:
				self.retrieveDownloadLinks(link, links) # Get the file urls for the course

			downloading = []  # List of currently downloading elements
			for i in range(len(self.downloadList)):
				element = self.downloadList.pop(0)
				started = self.downloadElement(element)  # Start downloading
				if started != False:
					downloading.append(element)
				time.sleep(0.1)

			WebDriverWait(self.driver, 120, 1).until(self.downloads_finish) # Wait for the downloads to finish
			time.sleep(10)

			files = os.listdir(self.downloads_folder) # List the downloaded course files
			for f in files:
				file_path = os.path.join(self.downloads_folder,f)
				if '.' in f and isfile(file_path):
					try:
						move(file_path, current_course_folder)
					except:
						os.remove(file_path)
			self.driver.get(KAMPUS_PAGE_URL)
			time.sleep(1)
			courseLinks = self.getCourses()

	def getLanguage(self):
		self.waitFor('tasiyici', BY_CLASS)
		language = self.driver.find_element_by_xpath(
			"/html/body/form/div[3]/div[1]/div[1]/table/tbody/tr/td[5]/a").text
		if language == "English":
			self.language = "TR"
		else:
			self.language = "EN"

	def getCourses(self):
		self.waitFor(MENU_AGACI, BY_CLASS)
		courses = self.driver.find_elements_by_xpath(
			"/html/body/form/div[3]/div[3]/div[2]/div/div[1]/ul/li/ul/li/a")
		return courses

	def getCourseName(self, url):
		self.driver.get(url+"/SinifBilgileri")
		ders_kodu = self.driver.find_element_by_xpath(
			"/html/body/form/div[3]/div[3]/div[3]/div/table[1]/tbody/tr[1]/td[2]").text
		ders_ismi = self.driver.find_element_by_xpath(
			'/html/body/form/div[3]/div[3]/div[3]/div/table[1]/tbody/tr[3]/td[2]/em').text
		return ders_kodu + " - " + ders_ismi

	def retrieveDownloadLinks(self, link, links):
		self.driver.get(link)

		rows = self.driver.find_elements_by_xpath(
			"/html/body/form/div[3]/div[3]/div[3]/div/div[2]/table[2]/tbody/tr/td[1]")
		images = self.driver.find_elements_by_xpath(
			"/html/body/form/div[3]/div[3]/div[3]/div/div[2]/table[2]/tbody/tr/td[1]/img")
		urls = self.driver.find_elements_by_xpath(
			"/html/body/form/div[3]/div[3]/div[3]/div/div[2]/table[2]/tbody/tr/td[1]/a")
		dates = self.driver.find_elements_by_xpath(
			"/html/body/form/div[3]/div[3]/div[3]/div/div[2]/table[2]/tbody/tr/td[3]")
		if(urls == []):
			return
		for i in range(len(rows)):
			name = rows[i].text
			url = urls[i].get_attribute("href")
			date = self.decodeDate(dates[i].text)
			img = images[i].get_attribute("src")
			if('folder' in img):
				links.append(url)
			else:
				file_dict = {'name': name, 'url': url, 'date': date}
				self.downloadList.append(file_dict)

	def decodeDate(self, date):
		months = MONTHS_TR if self.language == "TR" else MONTHS_EN
		dateOfFile = date[-10:-6]
		for index, month in enumerate(months):
			if month in date:
				if(index < 9):
					mon = "0" + str(index+1)
				elif (index == 9):
					mon = "10"
				else:
					mon = str(index+1)
				dateOfFile += mon
				dateOfFile += date[:2]
		return dateOfFile

	def checkDownloadLogs(self, new_link, new_date):
		if(os.path.isfile("download.log")):
			f = open("download.log", 'r')
			lines = f.readlines()
			for line in lines:
				line = line.split(',')
				old_link = line[0]
				old_date = line[1]
				if (old_link == new_link):
					if (int(old_date) < int(new_date)):
						f.close()
						return DOWNLOAD_AGAIN
					else:
						f.close()
						return DOWNLOAD_NOT
			f.close()
			return DOWNLOAD
		else:
			f = open('download.log', 'a')
			f.close()

	def downloadElement(self, element):
		status = self.checkDownloadLogs(element['url'], element['date'])
		if (status == DOWNLOAD):
			self.driver.get(element['url'])
			self.writeToLog(element['url']+","+element['date'])
		elif (status == DOWNLOAD_AGAIN):
			f = open("downloads.log", "r+")
			d = f.readlines()
			f.seek(0)
			for i in d:
				if not element['url'] in i:
					f.write(i)
			f.truncate()
			f.close()
			self.driver.get(element['url'])
			self.writeToLog(element['url']+","+element['date'])
		elif (status == DOWNLOAD_NOT):
			return False

	def downloads_finish(self, driver):
		if not driver.current_url.startswith("chrome://downloads"):
			driver.get("chrome://downloads/")
		return driver.execute_script("return document.querySelector('downloads-manager').shadowRoot.querySelector('#downloadsList').items.filter(e => e.state === 'COMPLETE').map(e => e.filePath || e.file_path || e.fileUrl || e.file_url);")

	def writeToLog(self, link):
		f = open("download.log", 'a')
		f.write(link)
		f.write('\n')
		f.close()


def getCredentials(debug=False):
	username = input("Ninova Username: ")
	try:
		password = getpass.getpass()
	except Exception as err:
		print('Error:', err)

	starred_pw = password[0]
	for i in range(0, len(password)-2):
		starred_pw += "*"
	starred_pw += password[-1]
	print("You entered: {} and {}".format(username, starred_pw))
	cont = input("Did you enter correctly (Y/N)")
	if (cont == "y" or cont == "Y"):
		return username, password
	else:
		return getCredentials()


def begin(username, password):
	ninova = Ninova(username, password)
	ninova.login()
	ninova.getLanguage()
	ninova.start()


if __name__ == '__main__':
	print("Welcome to Ninova Scraper...")
	print("Ninova Scraper is an automated tool that downloads every file on Ninova to your computer automatically.")
	username, password = getCredentials(debug=True)
	begin(username, password)
