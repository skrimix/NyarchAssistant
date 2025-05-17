fd -e py >po/POTFILES
xgettext -o po/nyarchassistant.pot $(fd -e py)
cd po
for file in $(fd -e po); do
	msgmerge -U "$file" nyarchassistant.pot
done
rm -f *~
