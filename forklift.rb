#!/usr/bin/env ruby

require 'sqlite3'

# Forklift helps you in heavy lifting tasks where you need to parallelise
# a number of jobs.
#
# ==== Example
#
# Fleet of forklifts:
#
#   forklift = Forklift.new("memo")
#   forklift.clear
#   forklift.load(['foo', 'bar', 'baz', 'quux'])
#   forklift.fleet(3) do |job, id|
#     puts "#{id} works on #{job}"
#     sleep 0.5
#   end
#
# Or just one forklift:
#
#   Forklift.new("memo").clear.load(%w(foo bar baz quux)).one do |job, id|
#     puts "#{id} works on #{job}"
#     sleep 0.5
#   end
#
# Delete a jobs:
#
#   Forklift.new("memo").remove(["quux", "foo"])
class Forklift
  DELAY = 0.1
  STATUSES = { ready: 0, current: 1, done: 2, removed: 3, error: 4, paused: 5 }
  REV_STATUSES = STATUSES.invert

  # Create a memo
  def initialize(memo_file)
    @memo_file = memo_file
    @rescue_errors = false
    with_database do |db|
      db.execute('CREATE TABLE IF NOT EXISTS jobs (name, status)')
      db.execute('CREATE TABLE IF NOT EXISTS errors (error_at, job_id, message, backtrace)')
      db.execute('UPDATE jobs SET status = ? WHERE status = ?', STATUSES[:ready], STATUSES[:progress])
    end
  end

  def clear
    with_database do |db|
      db.execute('DELETE FROM jobs')
      db.execute('DELETE FROM errors')
    end
    self
  end

  def errorstream=(stream)
    @errorstream = stream
  end

  def rescue_errors
    @rescue_errors = true
    self
  end

  def load(jobs)
    with_database do |db|
      stubbornly_execute(db) do
        jobs.each do |job|
          db.execute('INSERT INTO jobs (name, status) VALUES (?, ?)', job, STATUSES[:ready])
        end
      end
    end
    self
  end

  def set(jobs, status)
    status = STATUSES[status]
    unless status
      STDERR.puts STATUSES.keys.join(', ')
      exit 1
    end
    with_database do |db|
      stubbornly_execute(db) do
        jobs.each do |job|
          db.execute('UPDATE jobs SET status = ? WHERE name = ?', status, job)
        end
      end
    end
    self
  end

  def setall(from, to)
    from = STATUSES[from]
    to = STATUSES[to]
    unless from && to
      STDERR.puts STATUSES.keys.join(', ')
      exit 1
    end
    with_database do |db|
      stubbornly_execute(db) do
        db.execute('UPDATE jobs SET status = ? WHERE status = ?', to, from)
      end
    end
    self
  end

  def list(status = nil)
    with_database do |db|
      status = STATUSES[status.to_sym] rescue nil
      result = 
        if status
          stubbornly_execute(db, 'SELECT name, status FROM jobs WHERE status = ?', status)
        else
          stubbornly_execute(db, 'SELECT name, status FROM jobs')
        end
      result.map { |row|
        [row[0], REV_STATUSES[row[1]]]
      }
    end
  end

  def one(&body)
    run(0, &body)
  end

  def fleet(processors, &body)
    processors.times do |processor|
      fork do
        run(processor, &body)
      end
    end
    Process.waitall
  end

  private
  def stubbornly_execute(db, statement=nil, *args)
    if block_given?
      stubbornly_execute(db, 'BEGIN EXCLUSIVE')
      yield
      db.execute('END')
    else
      loop do
        begin
          return db.execute(statement, *args)
        rescue SQLite3::BusyException
          sleep(DELAY)
        end
      end
    end
  end

  def run(processor)
    with_database do |db|
      id = nil
      loop do
        stubbornly_execute(db, 'BEGIN EXCLUSIVE')
        id, job = db.get_first_row('SELECT ROWID, name FROM jobs WHERE status = 0 LIMIT 1')
        break unless id
        db.execute('UPDATE jobs SET status = 1 WHERE ROWID = ?', id)
        db.execute('END')

        begin
          yield job, processor
        rescue => e
          if @rescue_errors
            stubbornly_execute(db, 'INSERT INTO errors (error_at, job_id, message, backtrace) VALUES (CURRENT_TIMESTAMP, ?, ?, ?)', id, e.message, e.backtrace.join("\n"))
            stubbornly_execute(db, 'UPDATE jobs SET status = 4 WHERE ROWID = ?', id)
          else
            raise
          end
        end

        stubbornly_execute(db, 'UPDATE jobs SET status = 2 WHERE ROWID = ?', id)
      end
    end
  end

  def with_database
    db = SQLite3::Database.new(@memo_file)
    result = yield db
    db.close
    result
  end
end

if $0 == __FILE__
  def help_and_exit
    puts <<HELP
Syntax: $0 <queue> <command> <arguments>

Commands:
    clear
      clear a queue
    load <job>...
      adds jobs to the queue
    loadall <file>
      adds jobs from a file
    set <status> <job>...
      sets the specified jobs to that status
    setall <from_status> <to_status>
      sets all jobs of one status to another
    list [status]
      lists all jobs, or all jobs of that status
    run <num_processes> <commandline>
      runs the command for each ready job,
      replacing the string {} with the job name

Statuses:
    ready
      the job is not processed yet
      will be automatically scheduled next run
    current
      the job has started, but not finished
      will be automatically rescheduled next run
    done
      the job has successfully finished
      will not be processed again
    error
      the job has exit with an error
      intention: remove the error, try again
    removed
      the job has been removed
      intention: won't need it any more
    paused
      the job has been paused
      intention: will reschedule it manually later
HELP
    exit
  end

  help_and_exit if ARGV.empty?
  queue = ARGV.shift
  command = ARGV.shift
  help_and_exit unless %w(clear load loadall set setall list run).include?(command)
  forklift = Forklift.new(queue)
  case command
  when 'clear'
    forklift.clear
  when 'load'
    forklift.load(ARGV)
  when 'loadall'
    file = ARGV.shift
    jobsource =
      if file == '-'
        STDIN
      else
        File.read(joblist)
      end
    jobarray = jobsource.each_line.map(&:chomp)
    forklift.load(jobarray)
  when 'set'
    forklift.set(ARGV, ARGV.shift.to_sym)
  when 'setall'
    from = ARGV.shift.to_sym
    to = ARGV.shift.to_sym
    forklift.setall(from, to)
  when 'list'
    forklift.list(ARGV.shift).each_with_index do |row, index|
      puts ([index] + row).join("\t")
    end
  when 'run'
    forklift.setall(:current, :ready)
    processors = ARGV.shift.to_i
    line = ARGV.join(' ')
    forklift.rescue_errors.fleet(processors) do |job, id|
      job_line = line.gsub('{}', job)
      system(job_line) or raise "Exit with status #{$?}"
    end
  else
    help_and_exit
  end
end
