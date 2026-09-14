./render_perf.py --server --encoder turbo-jpeg --auto  2> rca-turbo-auto.txt
./render_perf.py --server --encoder jpeg --auto  2> rca-jpeg-auto.txt
echo "Connect to server now..."
./render_perf.py --server --encoder turbo-jpeg --auto-client  2> rca-turbo-auto-client.txt
echo "Connect to server now..."
./render_perf.py --server --encoder jpeg --auto-client  2> rca-jpeg-auto-client.txt
